"""Low-cardinality durable worker counters."""

from sqlalchemy import BigInteger, String
from sqlalchemy.orm import Mapped, mapped_column

from ..base import Base


class OperationalCounterRow(Base):
    __tablename__ = "operational_counters"

    metric: Mapped[str] = mapped_column(String(64), primary_key=True)
    dimension: Mapped[str] = mapped_column(String(64), primary_key=True)
    value: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
