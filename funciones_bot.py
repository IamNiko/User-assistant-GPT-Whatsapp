
def load_system_prompts():
    try:
        with open('Prompt_Bas.txt', 'r', encoding='utf-8') as file:
            prompt_content = file.read()
            TECHNICAL_PROMPT = prompt_content
            SYSTEM_PROMPT = prompt_content
            QUICK_RESPONSE = prompt_content
    except FileNotFoundError:
        TECHNICAL_PROMPT = "No se pudo cargar el prompt técnico."
        SYSTEM_PROMPT = "No se pudo cargar el prompt de usuario."



def split_message(message: str, limit: int = MESSAGE_LIMIT) -> list:
    """Divide un mensaje largo en partes más pequeñas respetando palabras completas."""
    if len(message) <= limit:
        return [message]
    
    parts = []
    current_part = ""
    words = message.split()
    
    for word in words:
        if len(current_part) + len(word) + 1 <= limit:
            current_part += (" " + word if current_part else word)
        else:
            parts.append(current_part)
            current_part = word
    
    if current_part:
        parts.append(current_part)
    
    return parts

def is_valid_name(message: str) -> bool:
    """Valida si el texto proporcionado es un nombre válido."""
    invalid_words = {
        'ok', 'vale', 'bien', 'bueno', 'si', 'no', 'hola', 
        'para', 'por', 'que', 'cual', 'como', 'cuando',
        'porque', 'nose', 'nop', 'yes', 'yeah',
        'claro', 'dale', 'obvio', 'test', 'prueba',
        'entendido', 'entendi', 'comprendo', 'comprendido',
        'ya', 'te', 'he', 'dicho', 'dije'
    }
    
    text = message.lower().strip()
    words = text.split()
    
    return not (len(words) == 0 or
               any(word in invalid_words for word in words) or
               len(text) > 20 or
               re.search(r'[0-9@#$%^&*(),.?":{}|<>]', text) or
               any(x in text for x in ['porque', 'para que', 'por que', '?', '!', 'jaja', 'test']) or
               len(re.sub(r'[^a-zA-ZáéíóúñÁÉÍÓÚÑ\s]', '', text)) < 2)

def clean_name(name: str) -> str:
    """Limpia y formatea un nombre proporcionado."""
    prefixes = [
        r'^(?:me\s+llamo\s+)',
        r'^(?:soy\s+)',
        r'^(?:mi\s+nombre\s+es\s+)',
        r'^(?:ok\s+)',
        r'^(?:vale\s+vale\s+)',
        r'^(?:vale\s+)',
        r'^(?:hola\s+)',
        r'^(?:yo\s+)',
        r'^(?:pues\s+)',
    ]
    
    name = name.lower().strip()
    for prefix in prefixes:
        name = re.sub(prefix, '', name)
    
    return ' '.join(word.capitalize() for word in name.split())

def detect_role(message: str) -> str:
    """Detecta el rol del usuario basado en su mensaje."""
    roles = {
        "jugador": [r'j', r'jug', r'jugador', r'player', r'juego', r'tenista', r'1'],
        "staff": [r's', r'sta', r'staff', r'empleado', r'personal', r'trabajo', r'2'],
        "tecnico": [r't', r'tec', r'tecnico', r'servicio', r'mantenimiento', r'3']
    }
    
    msg = message.lower()
    for role, patterns in roles.items():
        if any(re.search(pattern, msg) for pattern in patterns):
            return role
    return None

def is_follow_up_query(current_msg: str) -> bool:
    """Determina si un mensaje es una consulta de seguimiento simple."""
    return current_msg.lower().strip() in QUICK_RESPONSES

@lru_cache(maxsize=100)
def get_cached_response(message_hash: str, context_hash: str) -> str:
    """Cache para respuestas frecuentes."""
    return QUICK_RESPONSES.get(message_hash, "")

def get_gpt4_response(message: str, context: Dict[str, Any], db: Session) -> str:
    """Obtiene una respuesta de GPT-4 considerando el contexto."""
    try:
        # Verificar si es una respuesta rápida
        msg_lower = message.lower().strip()
        if msg_lower in QUICK_RESPONSES:
            return QUICK_RESPONSES[msg_lower]

        # Seleccionar el prompt adecuado
        system_content = SYSTEM_PROMPTS['technical'] if context.get("role") == "tecnico" and context.get("tech_access") else SYSTEM_PROMPTS['user']

        messages = [
            {"role": "system", "content": system_content},
            {"role": "user", "content": message}
        ]
        
        # Solo agregar contexto si es necesario
        if not is_follow_up_query(message):
            recent_conversation = (
                db.query(Conversation)
                .filter(Conversation.sender == context.get("sender"))
                .order_by(Conversation.id.desc())
                .first()
            )
            
            if recent_conversation:
                messages.extend([
                    {"role": "user", "content": recent_conversation.message},
                    {"role": "assistant", "content": recent_conversation.response}
                ])

        response = client.chat.completions.create(
            model="gpt-4",
            messages=messages
        )
        return response.choices[0].message.content
    
    except Exception as e:
        print(f"GPT-4 Error: {e}")
        return f"Lo siento {context.get('name', '')}, ¿podrías reformular tu pregunta?"

@app.post("/webhook")
async def whatsapp_webhook(
    Body: str = Form(...),
    From: str = Form(...),
    db: Session = Depends(get_db)
):
    try:
        incoming_msg = Body.strip()
        sender = From.strip()
        
        # Inicializar o recuperar el estado del usuario
        user_state = user_states.get(sender, {
            "step": "inicio",
            "name": None,
            "role": None,
            "has_paid": False,
            "tech_access": False,
            "sender": sender
        })

        # Manejar el flujo de conversación
        if user_state["step"] == "inicio":
            bot_response = "¡Hola! Soy el asistente de P-KAP. ¿Podrías decirme tu nombre?"
            user_state["step"] = "nombre"
        
        elif user_state["step"] == "nombre":
            if is_valid_name(incoming_msg):
                user_state["name"] = clean_name(incoming_msg)
                bot_response = (
                    f"¡Gracias {user_state['name']}! ¿Eres jugador, personal del club o servicio técnico?\n"
                    "1️⃣ Jugador\n2️⃣ Staff\n3️⃣ Servicio Técnico"
                )
                user_state["step"] = "rol"
            else:
                bot_response = get_gpt4_response(
                    f"El usuario respondió '{incoming_msg}' cuando le pedí su nombre. Da una respuesta empática y amable explicando por qué necesitas su nombre real.",
                    user_state,
                    db
                )
        
        # ... [El resto del manejo de estados sigue igual]
        
        # Actualizar estado y guardar en base de datos
        user_states[sender] = user_state
        
        conversation = Conversation(
            sender=sender,
            message=incoming_msg,
            response=bot_response
        )
        db.add(conversation)
        db.commit()

        # Enviar respuesta
        message_parts = split_message(bot_response)
        for part in message_parts:
            twilio_client.messages.create(
                body=part,
                from_='whatsapp:+14155238886',
                to=sender
            )

        return {"status": "success"}
        
    except Exception as e:
        print(f"Error: {e}")
        db.rollback()
        return {"status": "error", "message": str(e)}

# Inicialización del diccionario de estados de usuario
user_states = {}