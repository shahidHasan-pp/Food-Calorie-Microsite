import pytest
from app.services.gemini_service import _extract_json_from_text, _encode_image
from pathlib import Path
import base64
import json


def test_extract_json_from_clean_text():
    raw = '{"dish_identified": true, "confidence_score": 80}'
    result = _extract_json_from_text(raw)
    assert result["dish_identified"] is True
    assert result["confidence_score"] == 80


def test_extract_json_strips_markdown_fences():
    raw = """```json
    {"dish_identified": true, "total_calories": 350}
    ```"""
    result = _extract_json_from_text(raw)
    assert result["dish_identified"] is True
    assert result["total_calories"] == 350


def test_extract_json_no_json_raises():
    with pytest.raises(ValueError, match="No JSON object found"):
        _extract_json_from_text("Sorry, I cannot identify this.")


def test_extract_json_with_extra_text():
    raw = 'Here is the result: {"dish_identified": false, "error": "no_food_detected"} Thank you.'
    result = _extract_json_from_text(raw)
    assert result["dish_identified"] is False


def test_encode_image(tmp_path):
    """Test that _encode_image reads a file and base64 encodes it correctly."""
    img_path = tmp_path / "test.jpg"
    img_path.write_bytes(b"\xff\xd8\xff" + b"\x00" * 50)  # minimal JPEG header

    encoded, mime = _encode_image(str(img_path))
    assert mime == "image/jpeg"
    decoded = base64.b64decode(encoded)
    assert decoded[:3] == b"\xff\xd8\xff"


def test_encode_image_png(tmp_path):
    img_path = tmp_path / "test.png"
    img_path.write_bytes(b"\x89PNG" + b"\x00" * 50)

    encoded, mime = _encode_image(str(img_path))
    assert mime == "image/png"


def test_encode_image_webp(tmp_path):
    img_path = tmp_path / "test.webp"
    img_path.write_bytes(b"RIFF" + b"\x00" * 50)

    encoded, mime = _encode_image(str(img_path))
    assert mime == "image/webp"
