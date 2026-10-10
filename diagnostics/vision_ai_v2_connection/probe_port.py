from pathlib import Path
import subprocess
import sys

child = subprocess.Popen(
    [sys.executable, "-u", str(Path(__file__).with_name("read_serial.py"))],
    stdout=subprocess.PIPE,
    stderr=subprocess.STDOUT,
    text=True,
)
try:
    output, _ = child.communicate(timeout=20)
except subprocess.TimeoutExpired:
    subprocess.run(["taskkill", "/PID", str(child.pid), "/T", "/F"], capture_output=True)
    output, _ = child.communicate(timeout=5)
    output += "\nSERIAL_PROBE_TIMEOUT\n"
print(output)
Path(__file__).with_name("port-probe.txt").write_text(output, encoding="utf-8")
