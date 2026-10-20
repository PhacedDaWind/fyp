"""Local YOLOv9 plate detection and global CCT OCR through ONNX Runtime."""
from dataclasses import dataclass
from io import BytesIO
import logging
import math
import re
from threading import Lock
from time import perf_counter

from PIL import Image, ImageOps, UnidentifiedImageError

from model_config import MODEL, ASSETS, model_root

_reader = None
_lock = Lock()
logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class PlateReading:
    plate: str
    confidence: float | None
    model: str


def simulated_reading(plate: str) -> PlateReading:
    return PlateReading(plate=plate, confidence=None, model='manual-simulator')


def _get_reader():
    global _reader
    if _reader is None:
        root = model_root().resolve()
        if any(not (root / name).is_file() for name in ASSETS):
            raise RuntimeError('Models are missing. Run python download_models.py and restart the API.')
        from fast_alpr import ALPR
        from open_image_models import create_detector
        # Explicit local paths prevent uploads from triggering network downloads.
        detector = create_detector(
            root / 'yolo-v9-t-640-license-plates-end2end.onnx',
            backend='yolo_v9', class_labels=('License Plate',), conf_thresh=.4,
            providers=['CPUExecutionProvider'])
        _reader = ALPR(detector=detector, ocr_model=None,
                       ocr_model_path=root / 'cct_s_v2_global.onnx',
                       ocr_config_path=root / 'cct_s_v2_global_plate_config.yaml',
                       ocr_device='cpu', ocr_providers=['CPUExecutionProvider'])
    return _reader


def _detect_and_read(reader, image):
    results = []
    for result in reader.predict(image):
        detection, ocr = result.detection, result.ocr
        box = detection.bounding_box
        text = ocr.text if ocr else ''
        scores = ocr.confidence if ocr else None
        if isinstance(scores, (list, tuple)):
            # The OCR also returns probabilities for blank padding positions.
            # Exclude them from the score for actual recognized characters.
            chars = scores[:len(text)]
            score = sum(chars) / len(chars) if chars else float('nan')
        else:
            score = float(scores) if scores is not None else float('nan')
        results.append((text, score, [box.x1, box.y1, box.x2, box.y2],
                        float(detection.confidence), ocr.region if ocr else None))
    return results


def recognize_photo(data: bytes) -> dict:
    try:
        with Image.open(BytesIO(data)) as source:
            if source.width * source.height > 20_000_000:
                raise ValueError('Image is too large (maximum 20 megapixels)')
            image = ImageOps.exif_transpose(source).convert('RGB')
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError) as exc:
        raise ValueError('Choose a valid image of at most 20 megapixels') from exc
    if image.width < 100 or image.height < 30:
        raise ValueError('Image is too small to read')
    image.thumbnail((2200, 2200))

    started = perf_counter()
    with _lock:
        try:
            import numpy as np
            reader = _get_reader()
            # Pillow supplies RGB; the detector expects OpenCV BGR.
            results = _detect_and_read(reader, np.asarray(image)[:, :, ::-1].copy())
        except Exception as exc:
            logger.exception('Plate recognition inference failed')
            raise RuntimeError('Plate recognition is unavailable. Check the model installation and API logs.') from exc

    candidates = []
    for text, score, box, detector_score, region in results:
        raw = str(text)
        normalized = re.sub(r'\s', '', raw).upper()
        compatible = bool(re.fullmatch(r'[A-Z0-9]{2,12}', normalized))
        confidence = float(score)
        candidates.append({'text': raw, 'plate': normalized if compatible else None,
                           'confidence': confidence if math.isfinite(confidence) else None,
                           'box': [int(v) for v in box],
                           'detection_confidence': detector_score,
                           'region': region})
    candidates.sort(key=lambda c: c['confidence'] if c['confidence'] is not None else -1, reverse=True)
    # Never strip Chinese characters to make a wrong result look plausible.
    # Multiple plates require an explicit selection in the photo test.
    only = candidates[0] if len(candidates) == 1 else None
    return {'plate': only['plate'] if only else None,
            'confidence': only['confidence'] if only else None,
            'model': MODEL, 'runtime': 'ONNX Runtime / CPU',
            'inference_ms': round((perf_counter() - started) * 1000, 1),
            'image_size': list(image.size),
            'detection_count': len(candidates),
            'status': 'not_detected' if not candidates else 'review' if any(c['text'] for c in candidates) else 'unreadable',
            'candidates': candidates, 'needs_review': True}
