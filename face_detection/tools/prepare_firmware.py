"""Create an independent Himax SDK scenario from the board camera example."""
from pathlib import Path
import shutil

root = Path(__file__).resolve().parents[1]
scenarios = root / 'sdk/EPII_CM55M_APP_S/app/scenario_app'
src = scenarios / 'tflm_yolov8_od'
dst = scenarios / 'tflm_yolov8_face'
shutil.copytree(src, dst, dirs_exist_ok=True)
shutil.copy2(root / 'firmware/face_inference.cpp', dst / 'cvapp_yolov8n_ob.cpp')
models=list((root/'models/vela').glob('*_vela.tflite'))
if len(models)!=1:
    raise RuntimeError('Compile exactly one Vela model before building the firmware')
data=models[0].read_bytes()
hash_value=2166136261
for byte in data:
    hash_value=((hash_value^byte)*16777619)&0xffffffff
(dst/'face_expected_model.h').write_text(f'#define FACE_MODEL_BYTES {len(data)}u\n#define FACE_MODEL_FNV 0x{hash_value:08x}u\n')
# Select only our model, independent of retained flags from earlier firmware.
path = dst / 'tflm_yolov8_od.c'
text = path.read_text(encoding='utf-8', errors='surrogateescape')
text = text.replace('    pinmux_init();', '    pinmux_init();\n    hx_drv_swreg_aon_set_appused1(0);')
path.write_text(text, encoding='utf-8', errors='surrogateescape')
# Include the I2C slave in TrustZone and interrupt configuration.
path = dst / 'drv_user_defined.mk'
text = path.read_text() + '\nDRIVERS_IP_INSTANCE += IIC_SLAVE0\n'
path.write_text(text)
print(dst)
