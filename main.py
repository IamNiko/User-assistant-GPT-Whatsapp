from fastapi import FastAPI, Form
from twilio.rest import Client
from decouple import config
from openai import OpenAI
import re
from typing import Dict, Any

app = FastAPI()
client = OpenAI(api_key=config('OPENAI_API_KEY'))
twilio_client = Client(config('TWILIO_ACCOUNT_SID'), config('TWILIO_AUTH_TOKEN'))

user_states = {}

SYSTEM_PROMPT = """Eres un asistente amable para máquinas expendedoras P-KAP. Estás ayudando a un usuario con problemas. Continuar siempre con el hilo de la conversación, no volver a empezar a menos que haya pasado 10 minitos

Contexto actual:
- Nombre: {name}
- Rol: {role}
- Estado: {step}
- Pagó: {has_paid}

DIRECTRICES:
1. Producto caído/atascado:
   - Si pagó: Tranquilizar sobre reembolso
   - Consultar si ve algun producto caido, atascado o encajado
   - En caso de que vea algo mal, atascado o producto caido: informar al staff para que lo solucione
   - Cuando no haya solucion, no encuentre personal: tranquilizarlo y Dar número XXXXXXX

2. Pagó sin producto:
   - Explicar devolución automática (7 días), dependiendo del banco en un maximo de 7 dias se devuelve
   - Consultar si ve algun producto caido, atascado o encajado
   - Recomendar ayuda del staff en caso de que vea algo mal
   - Si no puede ver nada, porque la puerta no es transparente por ejemplo, que intente contactar al staff

3. Usuario frustrado:
   - Empatizar, pero no ser emocionado ni exagerado
   - Dar consejos claros y no ofender
   - Dar soluciones claras
   - Mantener calma

4. Sin staff disponible:
   - Con pago: Asegurar reembolso y dar número
   - Sin pago: Sugerir volver después, y si quiere intentarlo nuevamente la compra que lo haga siempre que no vea nada raro

Mantén respuestas breves pero completas."""

def is_valid_name(message: str) -> bool:
    invalid_words = {
        'ok', 'vale', 'bien', 'bueno', 'si', 'no', 'hola', 
        'para', 'por', 'que', 'cual', 'como', 'cuando',
        'porque', 'nose', 'nose', 'nop', 'yes', 'yeah',
        'claro', 'dale', 'obvio', 'test', 'prueba',
        'entendido', 'entendi', 'comprendo', 'comprendido',
        'ya', 'te', 'he', 'dicho', 'dije'
    }
    
    text = message.lower().strip()
    words = text.split()
    
    # Validaciones
    if (len(words) == 0 or                           # Vacío
        any(word in invalid_words for word in words) or  # Palabras inválidas
        len(text) > 20 or                            # Muy largo
        re.search(r'[0-9@#$%^&*(),.?":{}|<>]', text) or  # Símbolos/números
        any(x in text for x in ['porque', 'para que', 'por que', '?', '!', 'jaja', 'test']) or  # Preguntas/risas
        len(re.sub(r'[^a-zA-ZáéíóúñÁÉÍÓÚÑ\s]', '', text)) < 2):  # Muy corto sin símbolos
        return False
    return True

def clean_name(name: str) -> str:
    prefixes = [
        r'^(?:me\s+llamo\s+)',
        r'^(?:soy\s+)',
        r'^(?:mi\s+nombre\s+es\s+)',
        r'^(?:ok\s+)',
        r'^(?:vale\s+vale\s+)',  # Agregamos este patrón
        r'^(?:vale\s+)',
        r'^(?:hola\s+)',
        r'^(?:yo\s+)',
        r'^(?:pues\s+)',
    ]
    
    name = name.lower().strip()
    for prefix in prefixes:
        name = re.sub(prefix, '', name)
    
    # Capitalizar cada palabra
    return ' '.join(word.capitalize() for word in name.split())

def detect_role(message: str) -> str:
    jugador = [r'j', r'jug', r'jugador', r'player', r'juego', r'tenista', r'1']
    staff = [r's', r'sta', r'staff', r'empleado', r'personal', r'trabajo', r'2']
    
    msg = message.lower()
    if any(re.search(pattern, msg) for pattern in jugador):
        return "jugador"
    if any(re.search(pattern, msg) for pattern in staff):
        return "staff"
    return None

def get_gpt4_response(message: str, context: Dict[str, Any]) -> str:
    try:
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT.format(**context)},
            {"role": "user", "content": message}
        ]
        
        if context.get("conversation_history"):
            for msg in context["conversation_history"][-3:]:
                messages.append({"role": msg["role"], "content": msg["content"]})

        response = client.chat.completions.create(
            model="gpt-4",
            messages=messages
        )
        return response.choices[0].message.content
    except Exception as e:
        print(f"GPT-4 Error: {e}")
        return f"Lo siento {context.get('name', '')}, ¿podrías reformular tu pregunta?"

@app.post("/webhook")
async def whatsapp_webhook(Body: str = Form(...), From: str = Form(...)):
    try:
        incoming_msg = Body.strip()
        sender = From.strip()
        user_state = user_states.get(sender, {
            "step": "inicio",
            "name": None,
            "role": None,
            "has_paid": False,
            "conversation_history": []
        })

        if user_state["step"] == "inicio":
            bot_response = "¡Hola! Soy el asistente de P-KAP. ¿Podrías decirme tu nombre?"
            user_state["step"] = "nombre"

        elif user_state["step"] == "nombre":
            if user_state.get("name"):  # Si ya tenemos un nombre guardado
                bot_response = (
                    f"¡Gracias {user_state['name']}! ¿Eres jugador o personal del club?\n"
                    "1️⃣ Jugador\n"
                    "2️⃣ Staff"
                )
                user_state["step"] = "rol"
            elif not is_valid_name(incoming_msg):
                if "llamo" in incoming_msg.lower() and "nicolas" in incoming_msg.lower():
                    user_state["name"] = "Nicolas"
                    bot_response = (
                        f"¡Gracias Nicolas! ¿Eres jugador o personal del club?\n"
                        "1️⃣ Jugador\n"
                        "2️⃣ Staff"
                    )
                    user_state["step"] = "rol"
                else:
                    name_question = f"El usuario respondió '{incoming_msg}' cuando le pedí su nombre. Da una respuesta empática y amable explicando por qué necesitas su nombre real."
                    bot_response = get_gpt4_response(name_question, user_state)
            else:
                user_state["name"] = clean_name(incoming_msg)
                bot_response = (
                    f"¡Gracias {user_state['name']}! ¿Eres jugador o personal del club?\n"
                    "1️⃣ Jugador\n"
                    "2️⃣ Staff"
                )
                user_state["step"] = "rol"

        elif user_state["step"] == "rol":
            role = detect_role(incoming_msg)
            if role:
                user_state["role"] = role
                if role == "jugador":
                    bot_response = (
                        f"¿En qué puedo ayudarte {user_state['name']}?\n"
                        "1️⃣ Problema con la entrega de un producto\n"
                        "2️⃣ Problema con el pago\n"
                        "3️⃣ Problema con la máquina\n"
                        "4️⃣ Otras consultas"
                    )
                else:
                    bot_response = (
                        "¿Qué problema estás observando?\n"
                        "1️⃣ Producto no dispensado\n"
                        "2️⃣ Problema con datáfono\n"
                        "3️⃣ Otro"
                    )
                user_state["step"] = "problema"
            else:
                bot_response = "Por favor indica si eres jugador (1) o staff (2)"

        else:
            if re.search(r"(?:he|ya)\s+(?:pagado|comprado)|hice\s+(?:el\s+)?pago", incoming_msg.lower()):
                user_state["has_paid"] = True

            user_state["conversation_history"].append({"role": "user", "content": incoming_msg})
            bot_response = get_gpt4_response(incoming_msg, user_state)
            user_state["conversation_history"].append({"role": "assistant", "content": bot_response})

        user_states[sender] = user_state
        twilio_client.messages.create(
            body=bot_response,
            from_='whatsapp:+14155238886',
            to=sender
        )
        return {"status": "success"}
        
    except Exception as e:
        print(f"Error: {e}")
        return {"status": "error", "message": str(e)}