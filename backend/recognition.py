"""Temporary image OCR adapter; replace it with the partner model later."""
from dataclasses import dataclass
from typing import Protocol
from io import BytesIO
import re
import subprocess

from PIL import Image, ImageEnhance, ImageOps, UnidentifiedImageError

@dataclass(frozen=True)
class PlateReading:
    plate: str
    confidence: float | None
    model: str

class Recognizer(Protocol):
    def recognize(self, image: bytes) -> PlateReading: ...

def simulated_reading(plate: str) -> PlateReading:
    return PlateReading(plate=plate, confidence=None, model='manual-simulator')


def recognize_photo(data: bytes) -> PlateReading | None:
    """Read a close-up plate photo. This baseline is not trained for Malaysian plates."""
    try:
        source = Image.open(BytesIO(data))
        if source.width * source.height > 20_000_000:
            raise ValueError('Image is too large (maximum 20 megapixels)')
        image = ImageOps.exif_transpose(source).convert('RGB')
    except (UnidentifiedImageError, OSError) as exc:
        raise ValueError('Choose a valid image file') from exc
    if image.width < 100 or image.height < 30:
        raise ValueError('Image is too small to read')

    image.thumbnail((2200, 2200))
    gray = ImageOps.grayscale(image)
    variants = (image, ImageOps.autocontrast(gray), ImageEnhance.Contrast(gray).enhance(2))
    candidates = []
    for variant in variants:
        output = BytesIO()
        variant.save(output, format='PNG')
        try:
            result = subprocess.run(
                ['tesseract', 'stdin', 'stdout', '-l', 'eng', '--psm', '7',
                 '-c', 'tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789'],
                input=output.getvalue(), capture_output=True, timeout=12, check=False,
            )
        except FileNotFoundError as exc:
            raise RuntimeError('OCR engine is unavailable on the server') from exc
        except subprocess.TimeoutExpired as exc:
            raise RuntimeError('OCR took too long; try a smaller photo') from exc
        if result.returncode:
            raise RuntimeError('OCR could not process this photo')
        candidate = re.sub(r'[^A-Z0-9]', '', result.stdout.decode('utf-8', errors='replace').upper())
        if re.fullmatch(r'[A-Z0-9]{2,12}', candidate):
            candidates.append(candidate)
    if not candidates:
        return None
    plate = max(dict.fromkeys(candidates), key=lambda value: (candidates.count(value), len(value)))
    return PlateReading(plate=plate, confidence=None, model='tesseract-baseline')
