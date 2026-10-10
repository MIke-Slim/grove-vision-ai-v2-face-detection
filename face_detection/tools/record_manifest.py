"""Record downloaded source versions, model hashes and local build artifacts."""
import hashlib
import json
import shutil
from pathlib import Path

root=Path(__file__).resolve().parents[1]
uno=root/'uno/.pio/build/uno/firmware.hex'
if uno.exists():
    shutil.copy2(uno,root/'artifacts/uno-face.hex')
paths=['models/yolov8n-face.pt','models/face-192-raw.onnx',
       'models/tflite/face-192_full_integer_quant.tflite',
       'models/vela/face-192_full_integer_quant_vela.tflite',
       'models/tflite/face-192-simplified_float32.tflite',
       'artifacts/v2-face-tested.img','artifacts/v2-face-rebuilt.img',
       'artifacts/uno-face.hex','tools/himax_vela.ini']
manifest={'sources':{
    'weights':'https://github.com/akanametov/yolo-face/releases/download/1.0.0/yolov8n-face.pt',
    'sdk':'https://github.com/HimaxWiseEyePlus/Seeed_Grove_Vision_AI_Module_V2',
    'sdk_commit':'d3265e20d75fe20faccbf185d24454ad08b2fda8',
    'conversion_reference':'https://github.com/HimaxWiseEyePlus/YOLOv8_on_WE2',
    'arm_gcc':'13.2.Rel1',
    'ultralytics':'8.0.173','torch':'2.2.2+cpu','tensorflow':'2.13.1','onnx2tf':'1.15.4','vela':'4.0.1'},
    'configuration':{'input':[1,192,192,3],'model_flash_offset':'0xB7B000',
                     'input_rotation':'90 degrees clockwise','box_coordinates':'original camera image',
                     'model_mapped_address':'0x3AB7B000','npu':'ethos-u55-64',
                     'confidence_threshold':0.35,'nms_iou':0.45,'max_faces':16,
                     'i2c_address':'0x62','packet_bytes':32},
    'tested_pair':{'firmware_sha256':'a4dab3cd6d0e79e19566e2941f6cab9f167a6da28b69f6449f9261cb4e7b1d12',
                   'model_sha256':'61f5c53cb6b869b225addbd36b70e6465002399a1d7f9c741c4224f44c57f91a',
                   'model_fnv32':'2f1a734b','hardware_validation':'passed for tested image, model and Uno; rebuilt V2 image not flashed'},
    'files':{}}
for relative in paths:
    path=root/relative
    manifest['files'][relative]={'bytes':path.stat().st_size,'sha256':hashlib.sha256(path.read_bytes()).hexdigest()}
(root/'manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
# pip freeze preserves a machine-specific wheel URL for tensorflow-intel.
lock=root/'requirements-conversion-lock.txt'
lines=lock.read_text(encoding='utf-8-sig').splitlines()
lines=['tensorflow-intel==2.13.1' if line.startswith('tensorflow-intel @') else line for line in lines]
lock.write_text('\n'.join(lines)+'\n',encoding='utf-8')
print(json.dumps(manifest['files'],indent=2))
