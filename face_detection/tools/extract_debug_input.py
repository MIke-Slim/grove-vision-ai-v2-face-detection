"""Extract the exact RGB model input from the local diagnostic UART log."""
import argparse
from pathlib import Path
from PIL import Image

root=Path(__file__).resolve().parents[1]
parser=argparse.ArgumentParser()
parser.add_argument('log',nargs='?',default='flash-input-debug.log')
args=parser.parse_args()
lines=(root/'logs'/args.log).read_text(encoding='utf-8').splitlines()
recording=False
parts=[]
for line in lines:
    if line.startswith('BOOT '):
        line=line[5:]
    if line=='DEBUG_RGB_BEGIN':
        recording=True; continue
    if line=='DEBUG_RGB_END':
        break
    if recording and len(line)==384 and all(c in '0123456789abcdef' for c in line):
        parts.append(line)
data=bytes.fromhex(''.join(parts))
assert len(data)==192*192*3,len(data)
Image.frombytes('RGB',(192,192),data).save(root/'data/v2-input.png')
print('Extracted',len(data),'RGB bytes')
