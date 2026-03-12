import logging
import uuid
from datetime import datetime

from sqlalchemy import Column, String, Integer, Text, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import DeclarativeBase, relationship

logger = logging.getLogger(__name__)


class Base(DeclarativeBase):
    pass


class Device(Base):
    __tablename__ = "devices"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    device_id = Column(String(255), unique=True, nullable=False, index=True)
    user_agent = Column(Text, nullable=True)
    ip_address = Column(String(64), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    assets = relationship("Asset", back_populates="device", lazy="select")
    tasks = relationship("Task", back_populates="device", lazy="select")

    def __repr__(self) -> str:
        return f"<Device device_id={self.device_id}>"


class Asset(Base):
    __tablename__ = "assets"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    device_id = Column(String(255), ForeignKey("devices.device_id"), nullable=False, index=True)
    file_path = Column(Text, nullable=False)
    file_type = Column(String(32), nullable=False)
    file_size = Column(Integer, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    device = relationship("Device", back_populates="assets")
    tasks = relationship("Task", back_populates="asset", lazy="select")

    def __repr__(self) -> str:
        return f"<Asset id={self.id} file_path={self.file_path}>"


class Task(Base):
    __tablename__ = "tasks"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    device_id = Column(String(255), ForeignKey("devices.device_id"), nullable=False, index=True)
    asset_id = Column(UUID(as_uuid=True), ForeignKey("assets.id"), nullable=False)
    task_type = Column(String(64), nullable=False, default="food_calorie_estimation")
    status = Column(String(32), nullable=False, default="pending")
    ai_response_json = Column(JSONB, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    device = relationship("Device", back_populates="tasks")
    asset = relationship("Asset", back_populates="tasks")

    def __repr__(self) -> str:
        return f"<Task id={self.id} status={self.status}>"
