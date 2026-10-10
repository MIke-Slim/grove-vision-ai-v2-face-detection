"""Export the existing face detector weights, excluding its landmark branch.

Three raw YOLOv8 heads avoid mixing box coordinates and confidence in one
quantization scale. DFL decode and NMS are implemented in the V2 firmware.
"""
import json
import argparse
import types
from pathlib import Path
import cv2
import numpy as np
import torch
from ultralytics import YOLO

root = Path(__file__).resolve().parents[1]
parser=argparse.ArgumentParser()
parser.add_argument('--image',type=Path,default=root/'data/face.jpg')
args=parser.parse_args()
size = 192
yolo = YOLO(str(root / 'models/yolov8n-face.pt'))
network = yolo.model.float().eval().fuse()
head = network.model[-1]
assert head.nc == 1 and head.reg_max == 16

def raw_forward(self, features):
    return tuple(torch.cat((self.cv2[i](features[i]), self.cv3[i](features[i])), 1)
                 for i in range(self.nl))

head.forward = types.MethodType(raw_forward, head)
dummy = torch.zeros(1, 3, size, size)
with torch.no_grad():
    print('Outputs:', [list(t.shape) for t in network(dummy)])
torch.onnx.export(network, dummy, str(root / 'models/face-192-raw.onnx'),
                  input_names=['images'], output_names=['head8', 'head16', 'head32'],
                  opset_version=13, do_constant_folding=True)

# Initial calibration: source image and face-centered crops, with controlled
# exposure and scale variations. This is a smoke-test set, not an accuracy set.
image = cv2.imread(str(args.image))
if image is None:
    raise FileNotFoundError(f'Place a positive face test image at {args.image}')
source = json.loads((root / 'logs/desktop-validation.json').read_text())
if source.get('image_path') and Path(source['image_path']).resolve()!=args.image.resolve():
    raise RuntimeError('Run validate_model.py with the same --image first')
crops = [image]
for box in source['checks'][0]['boxes']:
    if box['score'] < 0.7:
        continue
    x1, y1, x2, y2 = box['xyxy']
    side = max(x2-x1, y2-y1) * 4
    cx, cy = (x1+x2)/2, (y1+y2)/2
    crop = image[max(0, int(cy-side/2)):min(image.shape[0], int(cy+side/2)),
                 max(0, int(cx-side/2)):min(image.shape[1], int(cx+side/2))]
    if crop.size:
        crops.append(crop)
    if len(crops) >= 30:
        break
samples = []
for crop in crops:
    rgb = cv2.cvtColor(cv2.resize(crop, (size, size)), cv2.COLOR_BGR2RGB)
    for gain in [0.65, 1.0, 1.25]:
        samples.append(np.clip(rgb.astype(np.float32)*gain, 0, 255) / 255.0)
np.save(root / 'data/calibration.npy', np.stack(samples))
np.save(root / 'data/test-input.npy', np.array([cv2.cvtColor(cv2.resize(image, (size, size)), cv2.COLOR_BGR2RGB)], np.float32)/255.0)
print('Calibration samples:', len(samples))
