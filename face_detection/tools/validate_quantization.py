"""Compare float and INT8 face outputs on a local camera image and public demo."""
import json
import argparse
import os
os.environ['TF_CPP_MIN_LOG_LEVEL']='2'
from pathlib import Path
import numpy as np
from PIL import Image
import tensorflow as tf

root=Path(__file__).resolve().parents[1]
parser=argparse.ArgumentParser()
parser.add_argument('--images',nargs='+',type=Path)
args=parser.parse_args()
(root/'logs').mkdir(exist_ok=True)

def decode(outputs):
    candidates=[]
    for output in outputs:
        if output.shape[-1]!=65:
            output=np.transpose(output,(0,2,3,1))
        _,height,width,channels=output.shape
        assert channels==65 and height==width
        stride=192/height
        logits=output[0,:,:,64]
        scores=1/(1+np.exp(-logits))
        for y,x in zip(*np.where(scores>=0.35)):
            distances=output[0,y,x,:64].reshape(4,16)
            weights=np.exp(distances-distances.max(axis=1,keepdims=True))
            distances=(weights*np.arange(16)).sum(axis=1)/weights.sum(axis=1)*stride
            left,top,right,bottom=distances
            x1=max(0,(x+0.5)*stride-left); y1=max(0,(y+0.5)*stride-top)
            x2=min(192,(x+0.5)*stride+right); y2=min(192,(y+0.5)*stride+bottom)
            if x2>x1 and y2>y1:
                candidates.append([float(x1),float(y1),float(x2),float(y2),float(scores[y,x])])
    candidates.sort(key=lambda b:b[4],reverse=True)
    selected=[]
    for box in candidates:
        if all(iou(box,other)<=0.45 for other in selected):
            selected.append(box)
        if len(selected)>=16:
            break
    return selected

def iou(a,b):
    intersection=max(0,min(a[2],b[2])-max(a[0],b[0]))*max(0,min(a[3],b[3])-max(a[1],b[1]))
    union=(a[2]-a[0])*(a[3]-a[1])+(b[2]-b[0])*(b[3]-b[1])-intersection
    return intersection/union if union>0 else 0

def run(path,image):
    runner=tf.lite.Interpreter(model_path=str(path))
    runner.allocate_tensors()
    inp=runner.get_input_details()[0]
    data=image
    if inp['dtype']==np.int8:
        scale,zero=inp['quantization']
        data=np.clip(np.round(image/scale)+zero,-128,127).astype(np.int8)
    runner.set_tensor(inp['index'],data)
    runner.invoke()
    outputs=[]
    for out in runner.get_output_details():
        value=runner.get_tensor(out['index']).astype(np.float32)
        if out['dtype']==np.int8:
            scale,zero=out['quantization']; value=(value-zero)*scale
        outputs.append(value)
    return decode(outputs), [{'shape':d['shape'].tolist(),'type':str(d['dtype']),'quant':d['quantization']} for d in runner.get_output_details()]

float_path=next((root/'models/tflite').glob('*_float32.tflite'))
int8_path=next((root/'models/tflite').glob('*_full_integer_quant.tflite'))
report=[]
images=args.images or [p for p in [root/'data/face.jpg',root/'data/camera-before.jpg'] if p.exists()]
if not images:
    raise FileNotFoundError('Supply a positive face image using --images PATH')
for path in images:
    name=path.name
    image=np.array(Image.open(path).convert('RGB').resize((192,192)),dtype=np.float32)[None]/255.0
    float_boxes,_=run(float_path,image)
    int_boxes,tensors=run(int8_path,image)
    matches=[max((iou(b,other) for other in float_boxes),default=0) for b in int_boxes]
    record={'image':name,'float_count':len(float_boxes),'int8_count':len(int_boxes),
            'int8_boxes':int_boxes,'float_boxes':float_boxes,'matching_iou':matches,'outputs':tensors}
    print(json.dumps(record),flush=True)
    report.append(record)
(root/'logs/quantization-validation.json').write_text(json.dumps(report,indent=2))
if not report[0]['int8_count']:
    raise RuntimeError('Quantized detector found no faces on the public test image')
