"""Save bounded Uno face-detection output over USB serial."""
import argparse
import time
from pathlib import Path

import serial

root = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser()
parser.add_argument('--port', default='COM10')
parser.add_argument('--seconds', type=float, default=20)
parser.add_argument('--log', default='uno-inference.log')
args = parser.parse_args()
(root / 'logs').mkdir(exist_ok=True)

with serial.Serial(args.port, 115200, timeout=0.2) as device, (root / 'logs' / args.log).open('w', encoding='utf-8') as log:
    deadline = time.monotonic() + args.seconds
    while time.monotonic() < deadline:
        line = device.readline().decode('utf-8', errors='replace').rstrip()
        if line:
            log.write(line + '\n')
            log.flush()
            print(line, flush=True)
