"""Local XMODEM transfer with explicit phase logs and bounded waits.

Uses the address-preamble protocol documented by the Himax SDK sender.
"""
import argparse
import io
import time
from pathlib import Path
import serial
from xmodem import XMODEM

root=Path(__file__).resolve().parents[1]
parser=argparse.ArgumentParser()
parser.add_argument('--port',default='COM11')
parser.add_argument('--firmware',type=Path,default=root/'artifacts/v2-face-tested.img')
parser.add_argument('--model',type=Path,default=root/'models/vela/face-192_full_integer_quant_vela.tflite')
parser.add_argument('--firmware-only',action='store_true')
parser.add_argument('--model-only',action='store_true')
parser.add_argument('--chunk-size',type=int,default=262144)
args=parser.parse_args()
if args.firmware_only and args.model_only:
    parser.error('Choose at most one of --firmware-only and --model-only')
if args.chunk_size <= 0 or args.chunk_size % 128:
    parser.error('Chunk size must be a positive multiple of 128')

with serial.Serial(args.port,921600,timeout=0.5) as device:
    def command(value):
        device.write(value.encode()+b'\r')

    def wait_for(pattern,timeout=40,enter=False):
        deadline=time.monotonic()+timeout
        while time.monotonic()<deadline:
            line=device.readline()
            if line:
                print('DEVICE',repr(line),flush=True)
            if pattern in line:
                return
            if enter:
                command('1')
        raise RuntimeError('Device did not reach '+repr(pattern))

    def getc(size,timeout=1):
        device.timeout=min(timeout,10)
        data=device.read(size)
        if size==1 and data not in [b'',b'\x06',b'\x15',b'C']:
            print('CONTROL',repr(data),flush=True)
        return data or None

    def putc(data,timeout=1):
        written=device.write(data)
        if len(data)>100:
            time.sleep(0.003)
        return written

    def progress(total,success,errors):
        if total%1024==0 or errors:
            print('PACKETS',total,success,errors,flush=True)

    modem=XMODEM(getc,putc,mode='xmodem')
    def send(data,label):
        print('SEND',label,len(data),flush=True)
        if not modem.send(io.BytesIO(data),retry=8,timeout=10,callback=progress):
            raise RuntimeError('Transfer failed: '+label)
        print('SENT',label,flush=True)
        device.timeout=0.5
        wait_for(b'Do you want to end file transmission and reboot system? (y)',timeout=50)

    wait_for(b'Send data using the xmodem protocol from your terminal',enter=True)
    time.sleep(1)
    device.reset_input_buffer()
    command('1')
    if not args.model_only:
        image=args.firmware
        send(image.read_bytes(),'firmware')
    if not args.firmware_only:
        model=args.model.read_bytes()
        for offset in range(0,len(model),args.chunk_size):
            command('n')
            header=b'\xc0\x5a'+(0xB7B000+offset).to_bytes(4,'little')+b'\0'*4+b'\x5a\xc0'+b'\xff'*116
            send(header,'address '+hex(0xB7B000+offset))
            command('n')
            send(model[offset:offset+args.chunk_size],'model '+hex(offset))
    command('y')
    print('TRANSFER_COMPLETE',flush=True)
    deadline=time.monotonic()+12
    device.timeout=0.2
    while time.monotonic()<deadline:
        line=device.readline()
        if line:
            print('BOOT',line.decode('utf-8',errors='replace').rstrip(),flush=True)
