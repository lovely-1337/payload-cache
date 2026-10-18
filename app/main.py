from contextlib import asynccontextmanager
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, Response, status
from sqlalchemy.orm import Session

from app import service
from app.db import engine, get_session
from app.models import Base
from app.schemas import PayloadCreated, PayloadRequest, PayloadResponse
from app.transformer import Transformer, get_transformer


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Shortcut: create_all вместо миграций (Alembic). Для продакшена нужны миграции.
    Base.metadata.create_all(engine)
    yield


app = FastAPI(title="Payload cache", lifespan=lifespan)

SessionDep = Annotated[Session, Depends(get_session)]
TransformerDep = Annotated[Transformer, Depends(get_transformer)]


@app.post(
    "/payload", response_model=PayloadCreated, status_code=status.HTTP_201_CREATED
)
def create_payload(
    request: PayloadRequest,
    response: Response,
    session: SessionDep,
    transform: TransformerDep,
) -> PayloadCreated:
    payload, created = service.create_payload(session, request, transform)
    if created:
        message = "Payload created"
    else:
        # Тот же вход уже обрабатывали: 200 вместо 201 сообщает, что ничего нового не создано.
        response.status_code = status.HTTP_200_OK
        message = "Payload already exists"
    return PayloadCreated(id=payload.id, message=message)


@app.get("/payload/{payload_id}", response_model=PayloadResponse)
def read_payload(payload_id: int, session: SessionDep) -> PayloadResponse:
    payload = service.get_payload(session, payload_id)
    if payload is None:
        raise HTTPException(status_code=404, detail="Payload not found")
    return PayloadResponse(output=payload.output)
