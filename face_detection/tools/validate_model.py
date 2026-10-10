"""Verify the independent face checkpoint at desktop and target resolutions."""
import json
import argparse
import cv2
from pathlib import Path
from ultralytics import YOLO

root = Path(__file__).resolve().parents[1]
parser=argparse.ArgumentParser()
parser.add_argument('--image',type=Path,default=root/'data/face.jpg')
args=parser.parse_args()
(root/'logs').mkdir(exist_ok=True)
model = YOLO(str(root / 'models/yolov8n-face.pt'))
report = {'classes': model.names, 'image_path':str(args.image.resolve()), 'checks': []}
if len(model.names) != 1 or 'face' not in str(model.names).lower():
    raise RuntimeError(f'Expected one face class, received {model.names}')
for size in [640, 256, 192]:
    result = model.predict(str(args.image), imgsz=size, conf=0.25,
                           device='cpu', verbose=False)[0]
    boxes = [{'xyxy': b.xyxy[0].tolist(), 'score': float(b.conf[0])}
             for b in result.boxes]
    record = {'size': size, 'count': len(boxes), 'boxes': boxes,
              'image_shape': result.orig_shape, 'speed_ms': result.speed}
    report['checks'].append(record)
    cv2.imwrite(str(root / f'logs/face-{size}.jpg'), result.plot())
    print(json.dumps({'size': size, 'count': len(boxes)}, ensure_ascii=True))
(root / 'logs/desktop-validation.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
