import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from unittest.mock import patch, AsyncMock, MagicMock
from io import BytesIO
from PIL import Image
import json

from app.main import app


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def sample_jpeg_bytes():
    """Create a minimal valid JPEG image in-memory."""
    buf = BytesIO()
    img = Image.new("RGB", (100, 100), color=(200, 150, 100))
    img.save(buf, format="JPEG")
    buf.seek(0)
    return buf.read()


@pytest.fixture
def mock_gemini_success():
    """Mock a successful Gemini response for Chicken Biryani."""
    return {
        "dish_identified": True,
        "confidence_score": 88,
        "items": [
            {
                "name": "Chicken Biryani",
                "estimated_quantity": "1.5 cups",
                "calories": 420,
                "protein_g": 18,
                "carbs_g": 55,
                "fat_g": 15,
                "sugar_g": 4,
            }
        ],
        "total_calories": 420,
        "total_macros": {
            "protein_g": 18,
            "carbs_g": 55,
            "fat_g": 15,
            "sugar_g": 4,
        },
    }


@pytest.fixture
def mock_gemini_no_food():
    return {"dish_identified": False, "error": "no_food_detected"}


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_health_check():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/api/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"


@pytest.mark.asyncio
async def test_analyze_food_success(sample_jpeg_bytes, mock_gemini_success):
    """Happy path: valid image -> Gemini returns food -> 200 with nutrition data."""
    with (
        patch("app.routers.food.crud.get_or_create_device", new_callable=AsyncMock) as mock_device,
        patch("app.routers.food.save_image", new_callable=AsyncMock) as mock_save,
        patch("app.routers.food.crud.create_asset", new_callable=AsyncMock) as mock_asset,
        patch("app.routers.food.crud.create_task", new_callable=AsyncMock) as mock_task,
        patch("app.routers.food.call_gemini_vision", new_callable=AsyncMock) as mock_gemini,
        patch("app.routers.food.crud.update_task_result", new_callable=AsyncMock),
    ):
        mock_device.return_value = MagicMock()
        mock_save.return_value = ("/uploads/test.jpg", "jpg", len(sample_jpeg_bytes))
        mock_asset.return_value = MagicMock(id="asset-uuid")
        mock_task.return_value = MagicMock(id="task-uuid")
        mock_gemini.return_value = mock_gemini_success

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post(
                "/api/analyze-food",
                data={"device_id": "test-device-123"},
                files={"image": ("food.jpg", sample_jpeg_bytes, "image/jpeg")},
            )

    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert data["food_name"] == "Chicken Biryani"
    assert data["calories"] == 420
    assert data["protein"] == 18
    assert data["carbs"] == 55
    assert data["fat"] == 15
    assert data["sugar"] == 4
    assert data["confidence_score"] == 88


@pytest.mark.asyncio
async def test_analyze_food_no_food_detected(sample_jpeg_bytes, mock_gemini_no_food):
    """When Gemini says no food detected, return success=False."""
    with (
        patch("app.routers.food.crud.get_or_create_device", new_callable=AsyncMock),
        patch("app.routers.food.save_image", new_callable=AsyncMock) as mock_save,
        patch("app.routers.food.crud.create_asset", new_callable=AsyncMock) as mock_asset,
        patch("app.routers.food.crud.create_task", new_callable=AsyncMock) as mock_task,
        patch("app.routers.food.call_gemini_vision", new_callable=AsyncMock) as mock_gemini,
        patch("app.routers.food.crud.update_task_result", new_callable=AsyncMock),
    ):
        mock_save.return_value = ("/uploads/test.jpg", "jpg", len(sample_jpeg_bytes))
        mock_asset.return_value = MagicMock(id="asset-uuid")
        mock_task.return_value = MagicMock(id="task-uuid")
        mock_gemini.return_value = mock_gemini_no_food

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post(
                "/api/analyze-food",
                data={"device_id": "test-device-123"},
                files={"image": ("notfood.jpg", sample_jpeg_bytes, "image/jpeg")},
            )

    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is False
    assert data["error"] == "no_food_detected"


@pytest.mark.asyncio
async def test_analyze_food_missing_device_id(sample_jpeg_bytes):
    """Missing device_id should return 422 (validation error)."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post(
            "/api/analyze-food",
            files={"image": ("food.jpg", sample_jpeg_bytes, "image/jpeg")},
        )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_analyze_food_invalid_file_type():
    """Uploading a non-image file should return 400."""
    with (
        patch("app.routers.food.crud.get_or_create_device", new_callable=AsyncMock),
    ):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post(
                "/api/analyze-food",
                data={"device_id": "test-device-abc"},
                files={"image": ("document.pdf", b"%PDF-1.4", "application/pdf")},
            )
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_analyze_food_gemini_failure(sample_jpeg_bytes):
    """If Gemini raises an exception, return 502."""
    with (
        patch("app.routers.food.crud.get_or_create_device", new_callable=AsyncMock),
        patch("app.routers.food.save_image", new_callable=AsyncMock) as mock_save,
        patch("app.routers.food.crud.create_asset", new_callable=AsyncMock) as mock_asset,
        patch("app.routers.food.crud.create_task", new_callable=AsyncMock) as mock_task,
        patch("app.routers.food.call_gemini_vision", new_callable=AsyncMock) as mock_gemini,
        patch("app.routers.food.crud.update_task_result", new_callable=AsyncMock),
    ):
        mock_save.return_value = ("/uploads/test.jpg", "jpg", len(sample_jpeg_bytes))
        mock_asset.return_value = MagicMock(id="asset-uuid")
        mock_task.return_value = MagicMock(id="task-uuid")
        mock_gemini.side_effect = RuntimeError("Gemini timeout")

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post(
                "/api/analyze-food",
                data={"device_id": "test-device-abc"},
                files={"image": ("food.jpg", sample_jpeg_bytes, "image/jpeg")},
            )

    assert resp.status_code == 502
