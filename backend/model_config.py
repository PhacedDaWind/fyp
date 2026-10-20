"""Pinned public detector/OCR assets; no images are sent to these sources."""
import os
from pathlib import Path

MODEL = 'yolov9-t640+cct-s-v2-global'
ASSETS = {
    'yolo-v9-t-640-license-plates-end2end.onnx': (
        'https://github.com/ankandrew/open-image-models/releases/download/assets/yolo-v9-t-640-license-plates-end2end.onnx',
        'c3c1026ca7d0585dd88084d68182dd897113712fa734ae1557ca70174440c076'),
    'cct_s_v2_global.onnx': (
        'https://github.com/ankandrew/cnn-ocr-lp/releases/download/arg-plates/cct_s_v2_global.onnx',
        '384bbbd2cea3ef54761d3df70822ef3a349ee1a112aeafddbe0e3ba06bc6e47b'),
    'cct_s_v2_global_plate_config.yaml': (
        'https://github.com/ankandrew/cnn-ocr-lp/releases/download/arg-plates/cct_s_v2_global_plate_config.yaml',
        '0335c74a305173bb6f393efed0fde03cadeaa0b649ed8e19f431016d8232d0a6'),
}


def model_root():
    return Path(os.environ.get('PLATE_MODEL_DIR', Path(__file__).parent / 'models' / 'global-plates'))
