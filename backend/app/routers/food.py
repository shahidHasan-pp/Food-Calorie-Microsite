import logging
from fastapi import APIRouter, Depends, File, Form, Request, UploadFile, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import get_db
from app.database import crud
from app.services.image_service import validate_image, save_image
from app.services.gemini_service import call_gemini_vision
from app.models.schemas import AnalyzeFoodResponse

logger = logging.getLogger(__name__)
router = APIRouter()


def _build_success_response(ai_data: dict) -> AnalyzeFoodResponse:
    """
    Map parsed Gemini JSON to the simplified API response schema.
    Picks the first identified item as the primary food name.
    """
    items = ai_data.get("items", [])
    primary = items[0] if items else {}
    total = ai_data.get("total_macros", {})

    return AnalyzeFoodResponse(
        success=True,
        food_name=primary.get("name") or "Unknown Food",
        calories=ai_data.get("total_calories") or primary.get("calories"),
        protein=total.get("protein_g") or primary.get("protein_g"),
        carbs=total.get("carbs_g") or primary.get("carbs_g"),
        fat=total.get("fat_g") or primary.get("fat_g"),
        sugar=total.get("sugar_g") or primary.get("sugar_g"),
        confidence_score=ai_data.get("confidence_score"),
    )


@router.post("/analyze-food", response_model=AnalyzeFoodResponse)
async def analyze_food(
    request: Request,
    image: UploadFile = File(...),
    device_id: str = Form(...),
    db: AsyncSession = Depends(get_db),
) -> AnalyzeFoodResponse:
    """
    POST /api/analyze-food

    Accepts a food image + device_id, runs Gemini Vision analysis,
    persists device/asset/task records, and returns nutrition estimates.

    Flow (Facade pattern: single endpoint orchestrates all sub-services):
    1. Validate image
    2. Upsert device record
    3. Save image to filesystem
    4. Create asset record
    5. Create task record (pending)
    6. Call Gemini Vision API
    7. Update task record (completed / failed)
    8. Return structured response
    """
    logger.info("analyze-food request device_id=%s filename=%s", device_id, image.filename)

    # Step 1 - Validate image format & size header
    content_length = request.headers.get("content-length")
    validate_image(image, int(content_length) if content_length else None)

    # Step 2 - Upsert device
    user_agent = request.headers.get("user-agent")
    ip_address = request.client.host if request.client else None
    await crud.get_or_create_device(db, device_id, user_agent, ip_address)

    # Step 3 - Save image to filesystem
    file_path, file_type, file_size = await save_image(image)

    # Step 4 - Create asset record
    asset = await crud.create_asset(db, device_id, file_path, file_type, file_size)

    # Step 5 - Create task record
    task = await crud.create_task(db, device_id, asset.id)

    # Step 6 - Call Gemini Vision API
    try:
        ai_data = await call_gemini_vision(file_path)
    except Exception as exc:
        logger.error("Gemini Vision failed task_id=%s error=%s", task.id, exc)
        await crud.update_task_result(db, task, "failed", {"error": str(exc)})
        raise HTTPException(status_code=502, detail="AI service temporarily unavailable. Please try again.")

    # Step 7 - Update task record
    if not ai_data.get("dish_identified"):
        await crud.update_task_result(db, task, "completed", ai_data)
        logger.info("No food detected task_id=%s", task.id)
        return AnalyzeFoodResponse(
            success=False,
            error="no_food_detected",
            message="No food was detected in the image. Please upload a clear photo of food.",
        )

    await crud.update_task_result(db, task, "completed", ai_data)

    # Step 8 - Build and return response
    response = _build_success_response(ai_data)
    logger.info(
        "analyze-food success task_id=%s food=%s calories=%s",
        task.id,
        response.food_name,
        response.calories,
    )
    return response
