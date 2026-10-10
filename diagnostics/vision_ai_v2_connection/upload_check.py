from pathlib import Path
import subprocess
import sys

project = Path(__file__).resolve().parent
firmware = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else project / ".pio/build/uno/firmware.hex"
log_name = "upload-restore.txt" if len(sys.argv) > 1 else "upload-check.txt"
tool_dir = Path.home() / ".platformio/packages/tool-avrdude"
args = [
    str(tool_dir / "avrdude.exe"), "-v", "-p", "atmega328p",
    "-C", str(tool_dir / "avrdude.conf"), "-c", "arduino",
    "-b", "115200", "-D", "-P", "COM10",
    "-U", "flash:w:" + str(firmware) + ":i",
]
child = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
timed_out = False
try:
    output, _ = child.communicate(timeout=25)
except subprocess.TimeoutExpired:
    timed_out = True
    subprocess.run(["taskkill", "/PID", str(child.pid), "/T", "/F"], capture_output=True)
    output, _ = child.communicate(timeout=5)
    output += "\nUPLOAD_TIMEOUT\n"
print(output)
(project / log_name).write_text(output, encoding="utf-8")
sys.exit(124 if timed_out else child.returncode)
