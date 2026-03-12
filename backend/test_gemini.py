import asyncio
from app.services.gemini_service import call_gemini_vision

async def test():
    try:
        res = await call_gemini_vision("uploads/4a0b041b516a48cb8abb246beac27cae.jpg")
        print("Success:", res)
    except Exception as e:
        print("Failed:", e)

asyncio.run(test())
