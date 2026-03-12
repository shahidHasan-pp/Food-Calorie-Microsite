import logging
import uuid as uuid_lib
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.models import Device, Asset, Task

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Device CRUD
# ---------------------------------------------------------------------------

async def get_or_create_device(
    db: AsyncSession,
    device_id: str,
    user_agent: str | None,
    ip_address: str | None,
) -> Device:
    """Retrieve existing device or create a new one."""
    result = await db.execute(select(Device).where(Device.device_id == device_id))
    device = result.scalar_one_or_none()

    if device is None:
        device = Device(
            id=uuid_lib.uuid4(),
            device_id=device_id,
            user_agent=user_agent,
            ip_address=ip_address,
            created_at=datetime.utcnow(),
        )
        db.add(device)
        await db.commit()
        await db.refresh(device)
        logger.info("Created new device record device_id=%s", device_id)
    else:
        logger.debug("Found existing device device_id=%s", device_id)

    return device


# ---------------------------------------------------------------------------
# Asset CRUD
# ---------------------------------------------------------------------------

async def create_asset(
    db: AsyncSession,
    device_id: str,
    file_path: str,
    file_type: str,
    file_size: int,
) -> Asset:
    """Create a new asset record for an uploaded image."""
    asset = Asset(
        id=uuid_lib.uuid4(),
        device_id=device_id,
        file_path=file_path,
        file_type=file_type,
        file_size=file_size,
        created_at=datetime.utcnow(),
    )
    db.add(asset)
    await db.commit()
    await db.refresh(asset)
    logger.info("Created asset id=%s for device_id=%s", asset.id, device_id)
    return asset


# ---------------------------------------------------------------------------
# Task CRUD
# ---------------------------------------------------------------------------

async def create_task(
    db: AsyncSession,
    device_id: str,
    asset_id: uuid_lib.UUID,
    task_type: str = "food_calorie_estimation",
) -> Task:
    """Create a new task in pending state."""
    task = Task(
        id=uuid_lib.uuid4(),
        device_id=device_id,
        asset_id=asset_id,
        task_type=task_type,
        status="pending",
        created_at=datetime.utcnow(),
    )
    db.add(task)
    await db.commit()
    await db.refresh(task)
    logger.info("Created task id=%s status=pending for device_id=%s", task.id, device_id)
    return task


async def update_task_result(
    db: AsyncSession,
    task: Task,
    status: str,
    ai_response_json: dict | None,
) -> Task:
    """Update task status and store the AI response."""
    task.status = status
    task.ai_response_json = ai_response_json
    await db.commit()
    await db.refresh(task)
    logger.info("Updated task id=%s status=%s", task.id, status)
    return task
