"""Read firmware metadata without running or changing its model."""
import argparse
import json
import time
from pathlib import Path
import serial
from serial.tools import list_ports

parser = argparse.ArgumentParser()
parser.add_argument('--port', default='COM11')
args = parser.parse_args()
records = {'ports': [{'port': p.device, 'description': p.description, 'hwid': p.hwid}
                     for p in list_ports.comports()], 'responses': {}}
with serial.Serial(args.port, 921600, timeout=0.2) as device:
    time.sleep(1)
    device.reset_input_buffer()
    for command in ['AT+VER?', 'AT+STAT?', 'AT+MODEL?']:
        device.write((command + '\r\n').encode())
        output = bytearray()
        deadline = time.monotonic() + 1.5
        while time.monotonic() < deadline:
            output.extend(device.read(8192))
        records['responses'][command] = output.decode('utf-8', errors='replace')
out = Path(__file__).resolve().parents[1] / 'logs/device-before.json'
out.write_text(json.dumps(records, indent=2, ensure_ascii=False), encoding='utf-8')
print(json.dumps(records, indent=2, ensure_ascii=True))
