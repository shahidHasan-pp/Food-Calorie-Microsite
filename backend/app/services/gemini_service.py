import logging
import json
import re
import base64
from pathlib import Path
import httpx
from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

GEMINI_VISION_URL = (
    "https://generativelanguage.googleapis.com/v1beta/models/"
    "{model}:generateContent?key={key}"
)

SYSTEM_PROMPT = """You are a professional nutritionist and food recognition AI.

Your job is to analyze food images and estimate calories and macronutrients.

Rules:
- Identify visible food items.
- Estimate portion sizes.
- Return ONLY valid JSON, no extra text, no markdown fences.

Expected JSON format when food is detected:
{
  "dish_identified": true,
  "confidence_score": 85,
  "items": [
    {
      "name": "Food Name",
      "estimated_quantity": "1 serving",
      "calories": 400,
      "protein_g": 20,
      "carbs_g": 45,
      "fat_g": 12,
      "sugar_g": 5
    }
  ],
  "total_calories": 400,
  "total_macros": {
    "protein_g": 20,
    "carbs_g": 45,
    "fat_g": 12,
    "sugar_g": 5
  }
}

Expected JSON format when no food is detected:
{
  "dish_identified": false,
  "error": "no_food_detected"
}"""


def _encode_image(file_path: str) -> tuple[str, str]:
    """Read image file and return base64 encoded string with MIME type."""
    path = Path(file_path)
    suffix = path.suffix.lower().lstrip(".")

    mime_map = {
        "jpg": "image/jpeg",
        "jpeg": "image/jpeg",
        "png": "image/png",
        "webp": "image/webp",
    }
    mime_type = mime_map.get(suffix, "image/jpeg")

    with open(file_path, "rb") as f:
        encoded = base64.b64encode(f.read()).decode("utf-8")

    return encoded, mime_type


def _extract_json_from_text(text: str) -> dict:
    """Extract JSON object from model response text, stripping markdown fences if present."""
    # Remove markdown code fences
    clean = re.sub(r"```(?:json)?", "", text).strip()

    # Find first {...} block
    match = re.search(r"\{.*\}", clean, re.DOTALL)
    if not match:
        raise ValueError("No JSON object found in AI response")

    return json.loads(match.group())


async def call_gemini_vision(file_path: str) -> dict:
    """
    Send an image to the Gemini Vision API and return the parsed JSON response.

    Uses the Strategy pattern: the prompt text and image are composed dynamically
    before sending, keeping the HTTP call isolated and testable.
    """
    logger.info("Calling Gemini Vision API for file_path=%s", file_path)

    image_b64, mime_type = _encode_image(file_path)

    url = GEMINI_VISION_URL.format(
        model=settings.GEMINI_MODEL,
        key=settings.GEMINI_API_KEY,
    )

    payload = {
        "contents": [
            {
                "parts": [
                    {"text": SYSTEM_PROMPT},
                    {
                        "inline_data": {
                            "mime_type": mime_type,
                            "data": image_b64,
                        }
                    },
                ]
            }
        ],
        "generationConfig": {
            "temperature": 0.2,
            "topP": 0.8,
            "responseMimeType": "application/json",
        },
    }

    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(url, json=payload)

    if response.status_code != 200:
        logger.error(
            "Gemini API error status=%s body=%s",
            response.status_code,
            response.text[:500],
        )
        raise RuntimeError(f"Gemini API returned status {response.status_code}")

    data = response.json()
    logger.debug("Gemini raw response: %s", str(data)[:300])

    try:
        parts = data["candidates"][0]["content"]["parts"]
        raw_text = "".join([p.get("text", "") for p in parts])
    except (KeyError, IndexError) as exc:
        logger.error("Failed to extract text from Gemini response. Raw response: %s Error: %s", json.dumps(data), exc)
        raise RuntimeError("Failed to get AI response text") from exc

    try:
        parsed = _extract_json_from_text(raw_text)
        logger.info("Gemini response parsed successfully dish_identified=%s", parsed.get("dish_identified"))
        return parsed
    except Exception as exc:
        logger.error(
            "Failed to parse Gemini response JSON: %s. Raw AI response text was: %r. Finish reason: %s", 
            exc, 
            raw_text,
            data["candidates"][0].get("finishReason") if "candidates" in data else "unknown"
        )
        raise RuntimeError("Failed to parse AI response") from exc
