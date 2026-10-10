"""Convert the face ONNX model locally, using captured calibration images."""
import os
os.environ['TF_CPP_MIN_LOG_LEVEL']='2'
from pathlib import Path
import numpy as np
from PIL import Image
from onnx2tf import convert
import importlib
import onnx
from onnxsim import simplify
import tensorflow as tf

root=Path(__file__).resolve().parents[1]
samples=list(np.load(root/'data/calibration.npy'))
for path in sorted((root/'data/camera-calibration').glob('*.jpg')):
    rgb=np.array(Image.open(path).convert('RGB').resize((192,192)),dtype=np.float32)/255.0
    samples.append(rgb)
calibration=root/'data/calibration-combined.npy'
np.save(calibration,np.array(samples,dtype=np.float32))
print('Combined calibration samples:',len(samples),flush=True)
model,checked=simplify(onnx.load(root/'models/face-192-raw.onnx'))
if not checked:
    raise RuntimeError('ONNX simplification did not preserve outputs')
# TensorFlow tracing rejects ONNX node names that begin with '/'.
for node in model.graph.node:
    node.name='op_'+node.name.replace('/','_').replace('.','_')
onnx.save(onnx.shape_inference.infer_shapes(model),root/'models/face-192-simplified.onnx')
# Supply local images to the converter's shape/transpose validation too.
# Its default path downloads unrelated test images from the network.
importlib.import_module('onnx2tf.onnx2tf').download_test_image_data = lambda: np.array(samples[:20],dtype=np.float32)
keras_model=convert(input_onnx_file_path=str(root/'models/face-192-simplified.onnx'),
        output_folder_path=str(root/'models/tflite'),
        output_integer_quantized_tflite=False,
        batch_size=1,
        not_use_onnxsim=True,
        non_verbose=True)
converter=tf.lite.TFLiteConverter.from_keras_model(keras_model)
converter.optimizations=[tf.lite.Optimize.DEFAULT]
converter.target_spec.supported_ops=[tf.lite.OpsSet.TFLITE_BUILTINS_INT8]
converter.inference_input_type=tf.int8
converter.inference_output_type=tf.int8
converter.representative_dataset=lambda: ([np.array(image,dtype=np.float32)[None]] for image in samples)
(root/'models/tflite/face-192_full_integer_quant.tflite').write_bytes(converter.convert())
print('Full INT8 model generated.',flush=True)
