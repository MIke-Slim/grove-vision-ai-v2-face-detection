"""Bounded local flashing with Himax's XMODEM sender (no website involved)."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time

root=Path(__file__).resolve().parents[1]
parser=argparse.ArgumentParser()
parser.add_argument('--port',default='COM11')
parser.add_argument('--firmware',type=Path,default=root/'artifacts/v2-face-tested.img')
parser.add_argument('--model',type=Path,default=root/'models/vela/face-192_full_integer_quant_vela.tflite')
parser.add_argument('--dry-run',action='store_true',help='Check artifacts without opening a serial port')
args=parser.parse_args()
image=args.firmware.resolve()
model=args.model.resolve()
if image.stat().st_size>0x100000 or 0xB7B000+model.stat().st_size>0x1000000:
    raise RuntimeError('Firmware/model exceeds its flash partition')
manifest={p.name:{'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}
          for p in [image,model]}
(root/'logs').mkdir(exist_ok=True)
(root/'logs/flash-artifacts.json').write_text(json.dumps(manifest,indent=2))
print(json.dumps(manifest),flush=True)
if image.name=='v2-face-tested.img':
    tested=json.loads((root/'manifest.json').read_text(encoding='utf-8'))['tested_pair']
    if manifest[image.name]['sha256']!=tested['firmware_sha256'] or manifest[model.name]['sha256']!=tested['model_sha256']:
        raise RuntimeError('Tested firmware/model pair changed; rebuild firmware and pass --firmware artifacts/v2-face-rebuilt.img')
cmd=[sys.executable,'-u',str(root/'tools/flash_local.py'),'--port='+args.port,
     '--firmware',str(image),'--model',str(model)]
if args.dry_run:
    print('DRY_RUN_OK: inputs are within flash partitions; no device was opened.',flush=True)
    sys.exit(0)
env=os.environ.copy(); env['PYTHONIOENCODING']='utf-8'
log=root/'logs/flash-v2.log'
if log.exists():
    backup=root/'logs'/f'flash-v2-{int(time.time())}.log'
    log.replace(backup)
with log.open('w',encoding='utf-8') as stream:
    child=subprocess.Popen(cmd,stdout=stream,stderr=subprocess.STDOUT,env=env)
    print('Flasher PID',child.pid,flush=True)
    try:
        child.wait(timeout=360)
    except subprocess.TimeoutExpired:
        subprocess.run(['taskkill','/PID',str(child.pid),'/T','/F'],capture_output=True)
        child.wait()
        raise RuntimeError('Flasher timed out; inspect flash-v2.log')
text=log.read_text(encoding='utf-8')
print(text[-1200:],flush=True)
if child.returncode or 'TRANSFER_COMPLETE' not in text:
    raise RuntimeError('Firmware/model transfer did not complete')
