"""Capture local camera images for calibration before replacing the firmware."""
import base64
import json
import time
from pathlib import Path
import serial

root=Path(__file__).resolve().parents[1]
folder=root/'data/camera-calibration'
folder.mkdir(parents=True,exist_ok=True)
with serial.Serial('COM11',921600,timeout=0.3) as device:
    time.sleep(1)
    device.reset_input_buffer()
    for index in range(24):
        device.write(b'AT+SAMPLE=1\r\n')
        deadline=time.monotonic()+3
        while time.monotonic()<deadline:
            line=device.readline().decode('utf-8',errors='replace').strip()
            try:
                record=json.loads(line)
            except json.JSONDecodeError:
                continue
            encoded=record.get('data',{}).get('image')
            if encoded:
                (folder/f'{index:03d}.jpg').write_bytes(base64.b64decode(encoded))
                print('Captured',index,flush=True)
                break
        time.sleep(0.2)
