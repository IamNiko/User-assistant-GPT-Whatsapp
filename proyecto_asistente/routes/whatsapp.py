
from fastapi import APIRouter, Form, Depends
from sqlalchemy.orm import Session
from db.database import get_db
from services.user_state import handle_user_state

whatsapp_webhook = APIRouter()

@whatsapp_webhook.post("/")
async def webhook_handler(
    Body: str = Form(...),
    From: str = Form(...),
    db: Session = Depends(get_db)
):
    return handle_user_state(Body, From, db)
