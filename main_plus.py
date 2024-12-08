
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

def update_user_state(sender: str, state: Dict[str, Any]) -> None:
    """
    Actualiza el estado del usuario en el diccionario global.

    Este método es utilizado para actualizar el estado del usuario después de
    recibir un mensaje o después de enviar una respuesta. El estado del usuario
    se almacena en el diccionario global `user_states` utilizando el número de
    teléfono del usuario como clave.

    Args:
        sender (str): Número de teléfono del usuario.
        state (Dict[str, Any]): Diccionario que contiene el nuevo estado del
            usuario.
    """
    user_states[sender] = state

app = FastAPI()
client = OpenAI(api_key=config('OPENAI_API_KEY'))
twilio_client = Client(config('TWILIO_ACCOUNT_SID'), config('TWILIO_AUTH_TOKEN'))

def split_message(message: str, limit: int = 1500) -> list:
    """
    Splits a long message into smaller parts while respecting complete words.
    Optimized to handle long words and ensure good performance.

    Args:
        message (str): The message to be split.
        limit (int): The maximum length of each split part. Defaults to 1500.

    Returns:
        list: A list of strings where each string is a part of the original message 
              not exceeding the specified limit.
    """
    # Return the message as a single part if it's within the limit
    if len(message) <= limit:
        return [message]

    words = message.split()  # Split message into words
    parts = []  # List to store the parts of the message
    current_part = []  # Current part being constructed

    for word in words:
        # If a single word exceeds the limit, split the word itself
        if len(word) > limit:
            if current_part:
                # Append the current part to parts if not empty
                parts.append(" ".join(current_part))
                current_part = []
            # Split the long word into chunks of the specified limit
            parts.extend([word[i:i+limit] for i in range(0, len(word), limit)])
        elif sum(len(w) + 1 for w in current_part) + len(word) <= limit:
            # Add word to the current part if it fits within the limit
            current_part.append(word)
        else:
            # Otherwise, finalize the current part and start a new one
            parts.append(" ".join(current_part))
            current_part = [word]

    # Append any remaining words in the current part
    if current_part:
        parts.append(" ".join(current_part))

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
    """
    Checks if the given message is a valid name.

    Returns False if the message is empty, contains invalid words, is too long,
    contains special characters, or has a length of less than 2 without
    considering special characters.

    Args:
        message (str): The message to be validated.

    Returns:
        bool: True if the message is a valid name, False otherwise.
    """
    invalid_words = {
        # Common words that are not valid names
        'ok', 'vale', 'bien', 'bueno', 'si', 'no', 'hola', 
        'para', 'por', 'que', 'cual', 'como', 'cuando',
        'porque', 'nose', 'nose', 'nop', 'yes', 'yeah',
        'claro', 'dale', 'obvio', 'test', 'prueba',
        'entendido', 'entendi', 'comprendo', 'comprendido',
        'ya', 'te', 'he', 'dicho', 'dije'
    }

    text = message.lower().strip()
    words = text.split()

    # Check if the message is empty or contains invalid words
    if len(words) == 0 or any(word in invalid_words for word in words):
        return False

    # Check if the message is too long
    if len(text) > 20:
        return False

    # Check if the message contains special characters
    if re.search(r'[0-9@#$%^&*(),.?":{}|<>]', text):
        return False

    # Check if the message contains specific phrases
    if any(x in text for x in ['porque', 'para que', 'por que', '?', '!', 'jaja', 'test']):
        return False

    # Check if the message has a length of less than 2 without considering special characters
    if len(re.sub(r'[^a-zA-ZáéíóúñÁÉÍÓÚÑ\s]', '', text)) < 2:
        return False

    return True


def clean_name(name: str) -> str:
    """
    Cleans and formats a given name.

    It removes common prefixes from the name, such as "me llamo", "soy", "mi nombre es", etc.
    Then it capitalizes each word in the name and joins them with spaces.

    Args:
        name (str): The name to be cleaned and formatted.

    Returns:
        str: The cleaned and formatted name.
    """
    prefixes = [
        # Remove common prefixes from the name
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
    """
    Detects the role of the user based on the message provided.

    The role can be either "jugador", "staff", or "tecnico".
    If no role is detected, it returns None.

    Args:
        message (str): The message to be analyzed.

    Returns:
        str: The detected role, or None if no role is detected.
    """
    # The following are some common words that can be used to detect the role
    jugador = [
        r'j', r'jug', r'jugador', r'player', r'juego', r'tenista', r'1'
    ]
    staff = [
        r's', r'sta', r'staff', r'empleado', r'personal', r'trabajo', r'2'
    ]
    tecnico = [
        r't', r'tec', r'tecnico', r'servicio', r'mantenimiento', r'3'
    ]

    # Convert the message to lowercase to make it case-insensitive
    msg = message.lower()

    # Check if any of the words in the jugador pattern are present in the message
    if any(re.search(pattern, msg) for pattern in jugador):
        return "jugador"

    # Check if any of the words in the staff pattern are present in the message
    if any(re.search(pattern, msg) for pattern in staff):
        return "staff"

    # Check if any of the words in the tecnico pattern are present in the message
    if any(re.search(pattern, msg) for pattern in tecnico):
        return "tecnico"

    # If none of the above conditions are met, return None
    return None


def get_gpt4_response(message: str, context: Dict[str, Any], db: Session) -> str:
    """
    Gets a response from the GPT-4 model based on the message and context provided.

    Args:
        message (str): The message to be analyzed.
        context (Dict[str, Any]): The context of the user, including the role, name, and previous conversations.
        db (Session): The SQLAlchemy session to access the database.

    Returns:
        str: The response from the GPT-4 model.
    """
    try:
        # Select the appropriate prompt based on the role and tech access
        if context.get("role") == "tecnico" and context.get("tech_access"):
            with open("Prompt_Bas.txt", "r", encoding="utf-8") as f:
                # Read the prompt from the file
                system_content = f.read()

        else:
            with open("Prompt_Bas.txt", "r", encoding="utf-8") as f:
                # Read the prompt from the file
                system_content = f.read()

        # Create the messages for the GPT-4 model
        messages = [
            # The system message contains the prompt
            {"role": "system", "content": system_content},
            # The user message is the message to be analyzed
            {"role": "user", "content": message}
        ]

        # Get the recent conversation history from the database
        recent_conversations = (
            db.query(Conversation)
            .filter(Conversation.sender == context.get("sender"))
            .order_by(Conversation.id.desc())
            .limit(3)
            .all()
        )

        # Add the conversation history to the messages
        for conv in reversed(recent_conversations):
            messages.extend([
                # The user message is the message from the conversation history
                {"role": "user", "content": conv.message},
                # The assistant message is the response from the conversation history
                {"role": "assistant", "content": conv.response}
            ])

        # Create the response from the GPT-4 model
        response = client.chat.completions.create(
            model="gpt-4",
            messages=messages
        )

        # Return the response
        return response.choices[0].message.content
    
    except FileNotFoundError:
        # Handle the error if the file is not found
        print("Error: El archivo Prompt_Bas.txt no se encontró.")
        return "Lo siento, no pude acceder a las instrucciones del sistema. Intenta más tarde."
    except Exception as e:
        # Handle any other exceptions
        print(f"GPT-4 Error: {e}")
        return f"Lo siento {context.get('name', '')}, ¿podrías reformular tu pregunta?"

@app.post("/webhook")
async def whatsapp_webhook(
    Body: str = Form(...),
    From: str = Form(...),
    db: Session = Depends(get_db)
):
    """
    Handles incoming WhatsApp messages via a webhook.

    This function processes incoming messages from WhatsApp, manages user state,
    and generates appropriate bot responses based on the conversation flow.

    Parameters:
    - Body (str): The body of the incoming WhatsApp message.
    - From (str): The sender's WhatsApp number.
    - db (Session): The database session for accessing and storing conversation data.

    Returns:
    - dict: A JSON response indicating the success or error status of the message handling.

    The function follows a conversation flow based on user steps such as 'inicio', 'nombre',
    'rol', etc. It updates the user state, generates responses, and interacts with the
    OpenAI GPT-4 model for dynamic responses when necessary.

    Exceptions are caught and logged, with database transactions being rolled back on errors.
    """
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
            update_user_state(sender, user_state)
            bot_response = "¡Hola! Soy el asistente de P-KAP. ¿Podrías decirme tu nombre?"
            user_state["step"] = "nombre"
            update_user_state(sender, user_state)

        elif user_state["step"] == "nombre":
            update_user_state(sender, user_state)
            if user_state.get("name"):
                bot_response = (
                    f"¡Gracias {user_state['name']}! ¿Eres jugador, personal del club o servicio técnico?\n"
                    "1️⃣ Jugador\n"
                    "2️⃣ Staff\n"
                    "3️⃣ Servicio Técnico"
                )
                user_state["step"] = "rol"
                update_user_state(sender, user_state)
            elif not is_valid_name(incoming_msg):
                if "llamo" in incoming_msg.lower() and "paquete" in incoming_msg.lower():
                    user_state["name"] = "paquete"
                    bot_response = (
                        f"¡Gracias paquete! ¿Eres jugador, personal del club o servicio técnico?\n"
                        "1️⃣ Jugador\n"
                        "2️⃣ Staff\n"
                        "3️⃣ Servicio Técnico"
                    )
                    user_state["step"] = "rol"
                    update_user_state(sender, user_state)
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
                update_user_state(sender, user_state)

        elif user_state["step"] == "rol":
            update_user_state(sender, user_state)
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
                    update_user_state(sender, user_state)
                    
                elif role == "staff":
                    bot_response = (
                        f"¿Qué tipo de problema necesitas resolver {user_state['name']}?\n"
                        "1️⃣ Producto caído o atascado\n"
                        "2️⃣ Problema con datáfono/pagos\n"
                        "3️⃣ Necesito reiniciar la máquina\n"
                        "4️⃣ Otro problema"
                    )
                    user_state["step"] = "problema"
                    update_user_state(sender, user_state)
                else:  # tecnico
                    bot_response = "Por favor, introduce la clave de acceso técnico:"
                    user_state["step"] = "validacion_tecnica"
                    update_user_state(sender, user_state)
            else:
                bot_response = "Por favor indica si eres jugador (1), staff (2) o servicio técnico (3)"

        elif user_state["step"] == "problema":
            update_user_state(sender, user_state)
            if incoming_msg == "1":  # Problema con la entrega de un producto
                bot_response = (
                    "¡Entendido! ¿Qué problema estás experimentando exactamente?\n"
                    "1️⃣ El producto que quería no se entregó\n"
                    "2️⃣ Pagué, pero no recibí nada\n"
                    "3️⃣ Veo un producto atascado/caído en la máquina\n"
                    "4️⃣ Otro problema con la entrega de un producto"
                )
                user_state["step"] = "detalle_problema"
                update_user_state(sender, user_state)
            elif incoming_msg == "2":  # Problema con el pago
                bot_response = (
                    "Lo siento mucho por el inconveniente con el pago. Por favor, indícame más detalles:\n"
                    "1️⃣ Pagué pero no recibí el producto\n"
                    "2️⃣ No aparece el cargo en mi cuenta\n"
                    "3️⃣ Otro problema relacionado con el pago"
                )
                user_state["step"] = "detalle_pago"
                update_user_state(sender, user_state)
            elif incoming_msg == "3":  # Problema con la máquina
                bot_response = (
                    "Gracias por informarlo. Por favor, selecciona la descripción que mejor se ajuste:\n"
                    "1️⃣ La máquina no responde\n"
                    "2️⃣ Las luces no funcionan\n"
                    "3️⃣ El sistema de pago no funciona\n"
                    "4️⃣ Otro problema técnico con la máquina"
                )
                user_state["step"] = "detalle_maquina"
                update_user_state(sender, user_state)
            elif incoming_msg == "4":  # Otras consultas
                bot_response = (
                    "¡Entendido! Por favor, indícame cómo puedo ayudarte:\n"
                    "1️⃣ Información sobre el funcionamiento de la máquina\n"
                    "2️⃣ Consultar políticas de reembolso\n"
                    "3️⃣ Contactar con soporte técnico\n"
                    "4️⃣ Otro tipo de consulta"
                )
                user_state["step"] = "detalle_otros"
                update_user_state(sender, user_state)
            else:  # Opción no válida
                bot_response = (
                    "Por favor, selecciona una opción válida:\n"
                    "1️⃣ Problema con la entrega de un producto\n"
                    "2️⃣ Problema con el pago\n"
                    "3️⃣ Problema con la máquina\n"
                    "4️⃣ Otras consultas"
                )


        elif user_state["step"] == "detalle_problema":
            update_user_state(sender, user_state)
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
            update_user_state(sender, user_state)
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
                update_user_state(sender, user_state)
            else:
                bot_response = "Clave incorrecta. Por favor, intenta de nuevo o contacta a soporte."

        elif user_state["step"] == "menu_tecnico":
            update_user_state(sender, user_state)
            if not user_state.get("tech_access"):
                bot_response = "No tienes acceso técnico validado. Por favor, introduce la clave de acceso."
                user_state["step"] = "validacion_tecnica"
                update_user_state(sender, user_state)

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
                    update_user_state(sender, user_state)
                elif incoming_msg == "2":
                    bot_response = (
                        "Configuración de sistema. Selecciona:\n"
                        "1️⃣ Ajustes de motor\n"
                        "2️⃣ Parámetros de sensores\n"
                        "3️⃣ Configuración de dispensador\n"
                        "4️⃣ Volver al menú principal"
                    )
                    user_state["step"] = "config_sistema"
                    update_user_state(sender, user_state)
                elif incoming_msg == "3":
                    bot_response = (
                        "Mantenimiento preventivo:\n"
                        "1️⃣ Procedimientos diarios\n"
                        "2️⃣ Procedimientos semanales\n"
                        "3️⃣ Procedimientos mensuales\n"
                        "4️⃣ Volver al menú principal"
                    )
                    user_state["step"] = "mantenimiento"
                    update_user_state(sender, user_state)
                elif incoming_msg == "4":
                    bot_response = (
                        "Calibración de componentes:\n"
                        "1️⃣ Calibración de posicionamiento\n"
                        "2️⃣ Ajuste de sensores\n"
                        "3️⃣ Calibración de motores\n"
                        "4️⃣ Volver al menú principal"
                    )
                    user_state["step"] = "calibracion"
                    update_user_state(sender, user_state)
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
                        update_user_state(sender, user_state)
                    else:
                        if user_state["step"] == "diagnostico_errores":
                            update_user_state(sender, user_state)
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