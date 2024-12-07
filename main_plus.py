from fastapi import FastAPI, Form, HTTPException, Depends
from twilio.rest import Client
from decouple import config
from openai import OpenAI
import re
from typing import Dict, Any
import json
from sqlalchemy.orm import Session
from db import get_db
from models import Conversation, SessionLocal

app = FastAPI()
client = OpenAI(api_key=config('OPENAI_API_KEY'))
twilio_client = Client(config('TWILIO_ACCOUNT_SID'), config('TWILIO_AUTH_TOKEN'))

def split_message(message: str, limit: int = 1500) -> list:
    """
    Divide un mensaje largo en partes más pequeñas respetando palabras completas.
    Se usa 1500 como límite para tener margen de seguridad.
    """
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

try:
    with open('Prompt_Bas.txt', 'r', encoding='utf-8') as file:
        TECHNICAL_PROMPT = file.read()
except FileNotFoundError:
    print("Advertencia: No se encontró el archivo Prompt_Bas.txt")
    TECHNICAL_PROMPT = "Error al cargar el prompt técnico"

# Clave de acceso para técnicos (en producción debería estar en .env)
TECH_ACCESS_KEY = config("TECH_ACCESS_KEY")

user_states = {}

try:
    with open('Prompt_Bas.txt', 'r', encoding='utf-8') as file:
        prompt_content = file.read()
        TECHNICAL_PROMPT = prompt_content
        SYSTEM_PROMPT = prompt_content
except FileNotFoundError:
    TECHNICAL_PROMPT = "No se pudo cargar el prompt técnico."
    SYSTEM_PROMPT = "No se pudo cargar el prompt de usuario."


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
    
    if (len(words) == 0 or
        any(word in invalid_words for word in words) or
        len(text) > 20 or
        re.search(r'[0-9@#$%^&*(),.?":{}|<>]', text) or
        any(x in text for x in ['porque', 'para que', 'por que', '?', '!', 'jaja', 'test']) or
        len(re.sub(r'[^a-zA-ZáéíóúñÁÉÍÓÚÑ\s]', '', text)) < 2):
        return False
    return True

def clean_name(name: str) -> str:
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
    jugador = [r'j', r'jug', r'jugador', r'player', r'juego', r'tenista', r'1']
    staff = [r's', r'sta', r'staff', r'empleado', r'personal', r'trabajo', r'2']
    tecnico = [r't', r'tec', r'tecnico', r'servicio', r'mantenimiento', r'3']
    
    msg = message.lower()
    if any(re.search(pattern, msg) for pattern in jugador):
        return "jugador"
    if any(re.search(pattern, msg) for pattern in staff):
        return "staff"
    if any(re.search(pattern, msg) for pattern in tecnico):
        return "tecnico"
    return None

def get_gpt4_response(message: str, context: Dict[str, Any], db: Session) -> str:
    try:
        if context.get("role") == "tecnico" and context.get("tech_access"):
            with open("Prompt_Bas.txt", "r", encoding="utf-8") as f:
                system_content = f.read()

        else:
            with open("Prompt_Bas.txt", "r", encoding="utf-8") as f:
                system_content = f.read()


        messages = [
            {"role": "system", "content": system_content},
            {"role": "user", "content": message}
        ]
        
        # Obtener historial reciente de la base de datos
        recent_conversations = (
            db.query(Conversation)
            .filter(Conversation.sender == context.get("sender"))
            .order_by(Conversation.id.desc())
            .limit(3)
            .all()
        )
        
        for conv in reversed(recent_conversations):
            messages.extend([
                {"role": "user", "content": conv.message},
                {"role": "assistant", "content": conv.response}
            ])

        response = client.chat.completions.create(
            model="gpt-4",
            messages=messages
        )
        return response.choices[0].message.content
    
    except FileNotFoundError:
        print("Error: El archivo Prompt_Bas.txt no se encontró.")
        return "Lo siento, no pude acceder a las instrucciones del sistema. Intenta más tarde."
    except Exception as e:
        print(f"GPT-4 Error: {e}")
        return f"Lo siento {context.get('name', '')}, ¿podrías reformular tu pregunta?"

@app.post("/webhook")
async def whatsapp_webhook(
    Body: str = Form(...),
    From: str = Form(...),
    db: Session = Depends(get_db)
):
    print(f"Solicitud recibida. Body: {Body}, From: {From}")

    try:
        incoming_msg = Body.strip()
        sender = From.strip()
        user_state = user_states.get(sender, {
            "step": "inicio",
            "name": None,
            "role": None,
            "has_paid": False,
            "tech_access": False,
            "sender": sender,
            "conversation_history": [] 
        })

        if user_state["step"] == "inicio":
            bot_response = "¡Hola! Soy el asistente de P-KAP. ¿Podrías decirme tu nombre?"
            user_state["step"] = "nombre"

        elif user_state["step"] == "nombre":
            if user_state.get("name"):
                bot_response = (
                    f"¡Gracias {user_state['name']}! ¿Eres jugador, personal del club o servicio técnico?\n"
                    "1️⃣ Jugador\n"
                    "2️⃣ Staff\n"
                    "3️⃣ Servicio Técnico"
                )
                user_state["step"] = "rol"
            elif not is_valid_name(incoming_msg):
                if "llamo" in incoming_msg.lower() and "nicolas" in incoming_msg.lower():
                    user_state["name"] = "Nicolas"
                    bot_response = (
                        f"¡Gracias Nicolas! ¿Eres jugador, personal del club o servicio técnico?\n"
                        "1️⃣ Jugador\n"
                        "2️⃣ Staff\n"
                        "3️⃣ Servicio Técnico"
                    )
                    user_state["step"] = "rol"
                else:
                    name_question = f"El usuario respondió '{incoming_msg}' cuando le pedí su nombre. Da una respuesta empática y amable explicando por qué necesitas su nombre real."
                    bot_response = get_gpt4_response(name_question, user_state, db)
            else:
                user_state["name"] = clean_name(incoming_msg)
                bot_response = (
                    f"¡Gracias {user_state['name']}! ¿Eres jugador, personal del club o servicio técnico?\n"
                    "1️⃣ Jugador\n"
                    "2️⃣ Staff\n"
                    "3️⃣ Servicio Técnico"
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
                    user_state["step"] = "problema"
                    
                elif role == "staff":
                    bot_response = (
                        f"¿Qué tipo de problema necesitas resolver {user_state['name']}?\n"
                        "1️⃣ Producto caído o atascado\n"
                        "2️⃣ Problema con datáfono/pagos\n"
                        "3️⃣ Necesito reiniciar la máquina\n"
                        "4️⃣ Otro problema"
                    )
                    user_state["step"] = "problema"
                else:  # tecnico
                    bot_response = "Por favor, introduce la clave de acceso técnico:"
                    user_state["step"] = "validacion_tecnica"
            else:
                bot_response = "Por favor indica si eres jugador (1), staff (2) o servicio técnico (3)"

        elif user_state["step"] == "problema":
            if incoming_msg == "1":  # Problema con la entrega de un producto
                bot_response = (
                    "¡Entendido! ¿Qué problema estás experimentando exactamente?\n"
                    "1️⃣ El producto que quería no se entregó\n"
                    "2️⃣ Pagué, pero no recibí nada\n"
                    "3️⃣ Veo un producto atascado/caído en la máquina\n"
                    "4️⃣ Otro problema con la entrega de un producto"
                )
                user_state["step"] = "detalle_problema"
            elif incoming_msg == "2":  # Problema con el pago
                bot_response = (
                    "Lo siento mucho por el inconveniente con el pago. Por favor, indícame más detalles:\n"
                    "1️⃣ Pagué pero no recibí el producto\n"
                    "2️⃣ No aparece el cargo en mi cuenta\n"
                    "3️⃣ Otro problema relacionado con el pago"
                )
                user_state["step"] = "detalle_pago"
            elif incoming_msg == "3":  # Problema con la máquina
                bot_response = (
                    "Gracias por informarlo. Por favor, selecciona la descripción que mejor se ajuste:\n"
                    "1️⃣ La máquina no responde\n"
                    "2️⃣ Las luces no funcionan\n"
                    "3️⃣ El sistema de pago no funciona\n"
                    "4️⃣ Otro problema técnico con la máquina"
                )
                user_state["step"] = "detalle_maquina"
            elif incoming_msg == "4":  # Otras consultas
                bot_response = (
                    "¡Entendido! Por favor, indícame cómo puedo ayudarte:\n"
                    "1️⃣ Información sobre el funcionamiento de la máquina\n"
                    "2️⃣ Consultar políticas de reembolso\n"
                    "3️⃣ Contactar con soporte técnico\n"
                    "4️⃣ Otro tipo de consulta"
                )
                user_state["step"] = "detalle_otros"
            else:  # Opción no válida
                bot_response = (
                    "Por favor, selecciona una opción válida:\n"
                    "1️⃣ Problema con la entrega de un producto\n"
                    "2️⃣ Problema con el pago\n"
                    "3️⃣ Problema con la máquina\n"
                    "4️⃣ Otras consultas"
                )


        elif user_state["step"] == "detalle_problema":
            if re.search(r"(?:he|ya)\s+(?:pagado|comprado)|hice\s+(?:el\s+)?pago|si|exacto|efectivamente|claro", incoming_msg.lower()):
                user_state["has_paid"] = True
            
            # Determinar el contexto basado en la pregunta actual
            if "club" in incoming_msg.lower() or "personal" in incoming_msg.lower() or "alguien" in incoming_msg.lower():
                content = "El usuario pregunta sobre buscar personal del club para ayuda. Como jugador que ya pagó, ¿qué debería responderle?"
            else:
                content = incoming_msg
            
            user_state["conversation_history"].append({"role": "user", "content": content})
            bot_response = get_gpt4_response(content, user_state, db)
            user_state["conversation_history"].append({"role": "assistant", "content": bot_response})

        elif user_state["step"] == "validacion_tecnica":
            if incoming_msg == TECH_ACCESS_KEY:
                user_state["tech_access"] = True
                bot_response = (
                    "⚠️ ACCESO TÉCNICO CONCEDIDO ⚠️\n\n"
                    "PROCEDIMIENTO DE ACCESO AL SISTEMA:\n\n"
                    "ACCESO FÍSICO:\n"
                    "1. Localizar cofre en frente de máquina\n"
                    "2. Ingresar código: 7527\n"
                    "3. Retirar la llave\n"
                    "4. Insertar llave en cerradura\n"
                    "5. Tirar del panel para abrir\n\n"
                    "ACCESO AL SISTEMA:\n"
                    "1. En tablet, presionar 'admin'\n"
                    "2. Pulsar cuadro blanco para teclado\n"
                    "3. Cambiar a teclado numérico\n"
                    "4. Ingresar: 123456\n\n"
                    "Una vez dentro, ¿qué necesitas consultar?\n"
                    "1️⃣ Diagnóstico de errores\n"
                    "2️⃣ Configuración de sistema\n"
                    "3️⃣ Mantenimiento preventivo\n"
                    "4️⃣ Calibración de componentes"
                )
                user_state["step"] = "menu_tecnico"
            else:
                bot_response = "Clave incorrecta. Por favor, intenta de nuevo o contacta a soporte."

        elif user_state["step"] == "menu_tecnico":
            if not user_state.get("tech_access"):
                bot_response = "No tienes acceso técnico validado. Por favor, introduce la clave de acceso."
                user_state["step"] = "validacion_tecnica"

            else:
                if incoming_msg == "1":
                    bot_response = (
                        "Diagnóstico de errores. Por favor, indícame:\n"
                        "1️⃣ Código de error específico (ej: E001)\n"
                        "2️⃣ Descripción del problema\n"
                        "3️⃣ Consultar lista de errores\n"
                        "4️⃣ Volver al menú principal"
                    )
                    user_state["step"] = "diagnostico_errores"
                elif incoming_msg == "2":
                    bot_response = (
                        "Configuración de sistema. Selecciona:\n"
                        "1️⃣ Ajustes de motor\n"
                        "2️⃣ Parámetros de sensores\n"
                        "3️⃣ Configuración de dispensador\n"
                        "4️⃣ Volver al menú principal"
                    )
                    user_state["step"] = "config_sistema"
                elif incoming_msg == "3":
                    bot_response = (
                        "Mantenimiento preventivo:\n"
                        "1️⃣ Procedimientos diarios\n"
                        "2️⃣ Procedimientos semanales\n"
                        "3️⃣ Procedimientos mensuales\n"
                        "4️⃣ Volver al menú principal"
                    )
                    user_state["step"] = "mantenimiento"
                elif incoming_msg == "4":
                    bot_response = (
                        "Calibración de componentes:\n"
                        "1️⃣ Calibración de posicionamiento\n"
                        "2️⃣ Ajuste de sensores\n"
                        "3️⃣ Calibración de motores\n"
                        "4️⃣ Volver al menú principal"
                    )
                    user_state["step"] = "calibracion"
                else:
                    bot_response = (
                        f"Opción no válida. ¿Qué necesitas consultar {user_state['name']}?\n"
                        "1️⃣ Diagnóstico de errores\n"
                        "2️⃣ Configuración de sistema\n"
                        "3️⃣ Mantenimiento preventivo\n"
                        "4️⃣ Calibración de componentes"
                    )

        elif user_state["step"] in ["diagnostico_errores", "config_sistema", "mantenimiento", "calibracion"]:
                    if incoming_msg.lower() in ["ver acceso", "procedimiento", "como accedo", "acceso"]:
                        bot_response = (
                            "📋 PROCEDIMIENTO DE ACCESO AL SISTEMA 📋\n\n"
                            "ACCESO FÍSICO:\n"
                            "1. Localizar cofre en frente de máquina\n"
                            "2. Ingresar código: 7527\n"
                            "3. Retirar la llave\n"
                            "4. Insertar llave en cerradura\n"
                            "5. Tirar del panel para abrir\n\n"
                            "ACCESO AL SISTEMA:\n"
                            "1. En tablet, presionar 'admin'\n"
                            "2. Pulsar cuadro blanco para teclado\n"
                            "3. Cambiar a teclado numérico\n"
                            "4. Ingresar: 123456\n\n"
                            "¿Deseas continuar con tu consulta anterior?"
                        )
                    elif incoming_msg == "4":  # Volver al menú principal
                        bot_response = (
                            f"¿Qué necesitas consultar {user_state['name']}?\n"
                            "1️⃣ Diagnóstico de errores\n"
                            "2️⃣ Configuración de sistema\n"
                            "3️⃣ Mantenimiento preventivo\n"
                            "4️⃣ Calibración de componentes"
                        )
                        user_state["step"] = "menu_tecnico"
                    else:
                        if user_state["step"] == "diagnostico_errores":
                            if incoming_msg.upper().startswith('E'):
                                # Consulta de código de error específico
                                content = f"Proporciona información técnica detallada sobre el error {incoming_msg}"
                            else:
                                # Consulta general de diagnóstico
                                content = f"Como técnico, necesito información sobre: {incoming_msg}"
                        else:
                            # Para otros menús técnicos
                            content = f"Como técnico, necesito información sobre la opción {incoming_msg} del menú {user_state['step']}"
                        
                        if "conversation_history" not in user_state:
                            user_state["conversation_history"] = []
                        
                        user_state["conversation_history"].append({"role": "user", "content": content})
                        bot_response = get_gpt4_response(content, user_state, db)
                        user_state["conversation_history"].append({"role": "assistant", "content": bot_response})

                    if re.search(r"(?:he|ya)\s+(?:pagado|comprado)|hice\s+(?:el\s+)?pago|si|exacto|efectivamente|claro", incoming_msg.lower()):
                        user_state["has_paid"] = True

                    user_states[sender] = user_state

                    # Guardar en la base de datos
                    conversation = Conversation(
                        sender=sender,
                        message=incoming_msg,
                        response=bot_response
                    )
                    db.add(conversation)
                    db.commit()

                    # Dividir y enviar el mensaje en partes si es necesario
                    message_parts = split_message(bot_response)
                    for part in message_parts:
                        twilio_client.messages.create(
                            body=part,
                            from_='whatsapp:+14155238886',
                            to=sender
                        )

                    return {"status": "success"}
        
        else:  # Para usuarios no técnicos o consultas generales
            if re.search(r"(?:he|ya)\s+(?:pagado|comprado)|hice\s+(?:el\s+)?pago|si|exacto|efectivamente|claro", incoming_msg.lower()):
                user_state["has_paid"] = True
            
            user_state["conversation_history"].append({"role": "user", "content": incoming_msg})
            bot_response = get_gpt4_response(incoming_msg, user_state, db)
            user_state["conversation_history"].append({"role": "assistant", "content": bot_response})

        user_states[sender] = user_state
        
        # Guardar en la base de datos
        conversation = Conversation(
            sender=sender,
            message=incoming_msg,
            response=bot_response
        )
        db.add(conversation)
        db.commit()

        # Dividir y enviar el mensaje en partes si es necesario
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
        db.rollback()  # Revertir la transacción en caso de error
        return {"status": "error", "message": str(e)}