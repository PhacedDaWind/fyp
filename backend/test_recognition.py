from io import BytesIO
from unittest.mock import patch

import numpy as np
import pytest
from PIL import Image

from recognition import recognize_photo, MODEL


def photo_bytes(color=(255, 0, 0)):
    image = Image.new('RGB', (500, 120), color)
    output = BytesIO()
    image.save(output, format='PNG')
    return output.getvalue()


def read_results(results):
    rows = [(row[0], row[1], row[3], float(row[4]) if len(row)>4 else .8, 'Malaysia') for row in results]
    with patch('recognition._get_reader'), patch('recognition._detect_and_read', return_value=rows) as run:
        result = recognize_photo(photo_bytes())
        # The library expects BGR, not Pillow's RGB.
        np.testing.assert_array_equal(run.call_args.args[1][0, 0], [0, 0, 255])
        return result



def test_single_plate_normalizes_whitespace_and_exposes_measurements():
    result = read_results([['wxy 2841', .91, 0, [1, 2, 300, 100]]])
    assert result['plate'] == 'WXY2841'
    assert result['confidence'] == .91
    assert result['model'] == MODEL
    assert result['needs_review'] is True
    assert result['inference_ms'] >= 0
    assert result['candidates'][0]['text'] == 'wxy 2841'


def test_chinese_characters_are_preserved_and_never_silently_removed():
    result = read_results([['京A12345', .99, 0, [1, 2, 300, 100]]])
    assert result['plate'] is None
    assert result['candidates'][0]['text'] == '京A12345'
    assert result['candidates'][0]['plate'] is None


def test_multiple_plates_require_explicit_selection():
    result = read_results([['WXY2841', .8, 0, [1, 2, 300, 100]], ['ABC1234', .9, 0, [1, 2, 300, 100]]])
    assert result['plate'] is None
    assert result['candidates'][0]['plate'] == 'ABC1234'


def test_invalid_photo_rejected_without_loading_models():
    with patch('recognition._get_reader') as load:
        with pytest.raises(ValueError, match='valid image'):
            recognize_photo(b'not an image')
        load.assert_not_called()


def test_oversized_image_rejected_before_decode():
    with patch('recognition.Image.open') as source:
        source.return_value.__enter__.return_value.width = 6000
        source.return_value.__enter__.return_value.height = 4000
        with pytest.raises(ValueError, match='20 megapixels'):
            recognize_photo(b'large image')


def test_unreadable_photo_has_no_candidates():
    result = read_results([])
    assert result['plate'] is None
    assert result['candidates'] == []


def test_model_failure_is_reported_instead_of_falling_back_to_other_ocr():
    with patch('recognition._get_reader', side_effect=OSError('missing model')):
        with pytest.raises(RuntimeError, match='unavailable'):
            recognize_photo(photo_bytes())


def test_short_reading_is_exposed_instead_of_reported_as_no_detection():
    result = read_results([['S150', .698, 0, [10,20,100,80], .436]])
    assert result['detection_count'] == 1
    assert result['status'] == 'review'
    assert result['candidates'][0]['text'] == 'S150'
    assert result['candidates'][0]['detection_confidence'] == .436


def test_unreadable_detection_is_distinct_from_missing_detection():
    result = read_results([['', float('nan'), 0, [10,20,100,80], .8]])
    assert result['status'] == 'unreadable'
    assert result['detection_count'] == 1
    assert result['candidates'][0]['confidence'] is None
    assert read_results([])['status'] == 'not_detected'


def test_adapter_uses_actual_character_scores_and_preserves_unreadable_detection():
    from types import SimpleNamespace
    from unittest.mock import Mock
    from recognition import _detect_and_read
    box=SimpleNamespace(x1=1,y1=2,x2=100,y2=80)
    detection=SimpleNamespace(bounding_box=box,confidence=.8)
    ocr=SimpleNamespace(text='ABC12',confidence=[.9]*5+[.01]*5,region='Malaysia')
    reader=Mock()
    reader.predict.return_value=[SimpleNamespace(detection=detection,ocr=ocr), SimpleNamespace(detection=detection,ocr=None)]
    results=_detect_and_read(reader,np.zeros((100,100,3),dtype=np.uint8))
    assert results[0][0] == 'ABC12'
    assert results[0][1] == pytest.approx(.9)
    assert results[0][2] == [1,2,100,80]
    assert results[0][4] == 'Malaysia'
    assert results[1][0] == ''


def test_model_initialization_uses_only_prepared_local_files(tmp_path,monkeypatch):
    import recognition
    from model_config import ASSETS
    monkeypatch.setattr(recognition,'_reader',None)
    monkeypatch.setattr(recognition,'model_root',lambda:tmp_path)
    for name in ASSETS:
        (tmp_path/name).write_bytes(b'mocked-model')
    with patch('open_image_models.create_detector') as detector, patch('fast_alpr.ALPR') as factory:
        recognition._get_reader()
        recognition._get_reader()
        factory.assert_called_once()
        detector.assert_called_once()
        assert detector.call_args.args[0].parent == tmp_path
        assert factory.call_args.kwargs['ocr_model'] is None
        assert factory.call_args.kwargs['ocr_model_path'].parent == tmp_path
