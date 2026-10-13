from io import BytesIO
from types import SimpleNamespace
from unittest.mock import patch

import pytest
from PIL import Image

from recognition import recognize_photo


def photo_bytes():
    image = Image.new('RGB', (500, 120), 'white')
    output = BytesIO()
    image.save(output, format='PNG')
    return output.getvalue()


def test_photo_ocr_normalizes_and_votes():
    outputs = [b'WXY 2841\n', b'WXY2841\n', b'WXY284I\n']
    with patch('recognition.subprocess.run', side_effect=[SimpleNamespace(returncode=0, stdout=value) for value in outputs]) as run:
        reading = recognize_photo(photo_bytes())
    assert reading.plate == 'WXY2841'
    assert reading.model == 'tesseract-baseline'
    assert run.call_count == 3


def test_invalid_photo_rejected():
    with pytest.raises(ValueError, match='valid image'):
        recognize_photo(b'not an image')


def test_unreadable_photo_returns_none():
    with patch('recognition.subprocess.run', return_value=SimpleNamespace(returncode=0, stdout=b'\n')):
        assert recognize_photo(photo_bytes()) is None
