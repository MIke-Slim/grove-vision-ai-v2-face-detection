"""Save real V2 boot/inference output with a time limit."""
import argparse
import time
from pathlib import Path
import serial

root=Path(__file__).resolve().parents[1]
parser=argparse.ArgumentParser()
parser.add_argument('--port',default='COM11')
parser.add_argument('--seconds',type=float,default=20)
parser.add_argument('--log',default='v2-inference.log')
args=parser.parse_args()
(root/'logs').mkdir(exist_ok=True)
with serial.Serial(args.port,921600,timeout=0.2) as device, (root/'logs'/args.log).open('w',encoding='utf-8') as log:
    deadline=time.monotonic()+args.seconds
    while time.monotonic()<deadline:
        line=device.readline().decode('utf-8',errors='replace').rstrip()
        if line:
            log.write(line+'\n'); log.flush()
            if 'FACE' in line or 'HEAD' in line:
                print(line,flush=True)
