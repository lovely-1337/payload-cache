from sqlalchemy import String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class TransformedString(Base):
    """Кэш уровня 1: результат transformer для одной строки."""

    __tablename__ = "transformed_strings"

    source: Mapped[str] = mapped_column(Text, primary_key=True)
    result: Mapped[str] = mapped_column(Text)


class Payload(Base):
    """Кэш уровня 2: готовый output для конкретной пары списков."""

    __tablename__ = "payloads"

    id: Mapped[int] = mapped_column(primary_key=True)
    # sha256 входа: уникальность даёт переиспользование id
    input_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    output: Mapped[str] = mapped_column(Text)
