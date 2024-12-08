
from services.gpt_response import get_gpt4_response
from services.validation import detect_role, is_valid_name, clean_name
from db.models import Conversation

user_states = {}

def handle_user_state(body: str, sender: str, db):
    user_state = user_states.get(sender, {"step": "inicio", "conversation_history": []})
    # Lógica de manejo según `step`
    return {"status": "success"}
