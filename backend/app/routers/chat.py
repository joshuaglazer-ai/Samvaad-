from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..chat import handle_turn
from ..db import get_db
from ..schemas import ChatIn

router = APIRouter(prefix="/api", tags=["chat"])


@router.post("/chat")
def chat(body: ChatIn, db: Session = Depends(get_db)) -> dict:
    try:
        return handle_turn(db, body.session_id, body.speaker, body.text.strip(), body.language)
    except LookupError as exc:
        raise HTTPException(404, str(exc)) from exc
