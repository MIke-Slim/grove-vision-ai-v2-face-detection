from pathlib import Path
import time
import serial

log_path = Path(__file__).with_name("serial-check.txt")
print("OPENING_COM10", flush=True)
with serial.Serial("COM10", 115200, timeout=1) as port, log_path.open("w", encoding="utf-8") as log:
    print("COM10_OPENED", flush=True)
    end = time.monotonic() + 14
    while time.monotonic() < end:
        line = port.readline().decode("utf-8", errors="replace").strip()
        if line:
            print(line, flush=True)
            log.write(line + "\n")
            log.flush()
