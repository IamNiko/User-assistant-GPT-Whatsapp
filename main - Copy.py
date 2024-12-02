from fastapi import FastAPI, Form
from twilio.rest import Client
from decouple import config

app = FastAPI()

# Configuración de Twilio
account_sid = config('TWILIO_ACCOUNT_SID')
auth_token = config('TWILIO_AUTH_TOKEN')
twilio_client = Client(account_sid, auth_token)

# Almacén de estados de usuario
user_states = {}

@app.post("/webhook")
async def whatsapp_webhook(Body: str = Form(...), From: str = Form(...)):
    try:
        incoming_msg = Body.strip().lower()
        sender = From.strip()
        user_state = user_states.get(sender, {"step": "ask_name", "name": None, "role": None, "problem": None})

        # Detectar enfado o malestar
        def detect_anger(message):
            anger_keywords = ["mierda", "puta", "qué asco", "maldita", "qué porquería", "no funciona", "horrible", "nadaaaa"]
            return any(word in message for word in anger_keywords)

        # Reconocer problemas descriptivos relacionados con el ascensor
        def interpret_problem(message):

            # Palabras clave principales
            main_keywords = ["producto", "ascensor","bote", "tubo", "grip"]
            keywords = ["ascensor arriba", "mitad", "medio", "derecha", "izquierda", "no está abajo", "mal colocado", "trabado", "atascado", 
                        "encajado", "atorado", "frenado", "inclinado", "torcido", "enganchado", 
                                 "trancado", "bloqueado", "no baja", "se quedó", "no sale", "atasque", "mal colocado","caido", "tirado", 
                                 "piso", "abajo", "suelo", "fondo", "mal colocado",
                             "bloquea salida", "dentro de la máquina", "piso", "obstruido", "tirado en la máquina"]

            # Verificar combinación de "producto" con problemas
            if any(main in message for main in main_keywords):
                if "ascensor" in message and any(keyword in message for keyword in keywords):
                    return "3"  # Ascensor fuera de posición
                if "producto" in message and any(keyword in message for keyword in keywords):
                    return "1"  # Producto atascado
                if "producto" in message and any(keyword in message for keyword in keywords):
                    return "2"  # Producto caído

    # Si no se detecta ningún problema
    return None

        # Paso 1: Solicitar el nombre
        if user_state["step"] == "ask_name":
            bot_response = "¡Hola! Soy el asistente de P-KAP. ¿Cómo te llamas?"
            user_state["step"] = "welcome_user"

        # Paso 2: Interpretar el nombre o tranquilizar al usuario si está molesto
        elif user_state["step"] == "welcome_user":
            if detect_anger(incoming_msg):
                bot_response = (
                    "Entiendo que estás molesto. Lamento que estés teniendo una experiencia frustrante. Estoy aquí para ayudarte. "
                    "Por favor, ¿puedes decirme tu nombre para que pueda asistirte mejor?"
                )
            elif len(incoming_msg.split()) == 1 and incoming_msg.isalpha():
                user_state["name"] = incoming_msg.capitalize()
                bot_response = (
                    f"¡Encantado de conocerte, {user_state['name']}! ¿Eres un jugador o staff del club? Responde con:\n"
                    "1️⃣ Jugador\n"
                    "2️⃣ Staff del club"
                )
                user_state["step"] = "identify_role"
            else:
                bot_response = (
                    "No estoy seguro de haber entendido tu nombre. Por favor, repítelo para poder dirigirme correctamente a ti."
                )

        # Paso 3: Identificar rol
        elif user_state["step"] == "identify_role":
            if "jugador" in incoming_msg or incoming_msg == "1":
                user_state["role"] = "Jugador"
                bot_response = (
                    "Entendido. ¿En qué puedo ayudarte?\n"
                    "1️⃣ Problemas con pagos\n"
                    "2️⃣ Producto no entregado\n"
                    "3️⃣ Preguntas generales"
                )
                user_state["step"] = "player_issue"
            elif "staff" in incoming_msg or incoming_msg == "2":
                user_state["role"] = "Staff"
                bot_response = (
                    "Entendido. ¿En qué puedo ayudarte?\n"
                    "1️⃣ Problemas de dispensación\n"
                    "2️⃣ Datáfono\n"
                    "3️⃣ Conexiones/Energía"
                )
                user_state["step"] = "staff_issue"
            else:
                bot_response = "Por favor, selecciona una opción válida:\n1️⃣ Jugador\n2️⃣ Staff del club"

        # Paso 4: Problema del jugador
        elif user_state["step"] == "player_issue":
            if "pagado" in incoming_msg and ("nada" in incoming_msg or "producto" in incoming_msg or "entrega" in incoming_msg):
                bot_response = (
                    "Lamento mucho el inconveniente. Para ayudarte mejor, ¿puedes confirmarme si sucede alguna de estas situaciones?\n"
                    "1️⃣ ¿Hay un producto atascado?\n"
                    "2️⃣ ¿Hay un producto caído dentro de la máquina?\n"
                    "3️⃣ ¿El ascensor no está en su posición inicial (abajo a la izquierda)?\n\n"
                    "Responde con el número correspondiente o describe si observas algo más."
                )
                user_state["step"] = "identify_cause"
            else:
                bot_response = (
                    "¿Podrías darme más detalles sobre el problema que estás experimentando? Estoy aquí para ayudarte."
                )

        # Paso 5: Identificar causas del problema
        elif user_state["step"] == "identify_cause":
            problem_code = interpret_problem(incoming_msg)

            if problem_code:
                problems = {
                    "1": "producto atascado",
                    "2": "producto caído",
                    "3": "ascensor fuera de posición"
                }
                user_state["problem"] = problems[problem_code]
                bot_response = (
                    f"Entendido, parece que hay un {user_state['problem']}. Por favor, contacta al staff del club para resolver este problema. "
                    "¿Pudiste comunicarte con alguien del staff?"
                )
                user_state["step"] = "contact_staff"
            elif "no" in incoming_msg:
                bot_response = (
                    "Gracias por verificar. Dado que no observas problemas, puedes intentar nuevamente la compra. "
                    "No te preocupes, la compra anterior no será cobrada."
                )
                user_state["step"] = "final_step"
            else:
                bot_response = (
                    "No entiendo tu respuesta. Por favor, indícame si observas alguno de los problemas mencionados o describe lo que ves."
                )

        # Paso 6: Contactar al staff
        elif user_state["step"] == "contact_staff":
            if "no hay nadie" in incoming_msg or "no puedo contactar" in incoming_msg or "no quiero" in incoming_msg:
                bot_response = (
                    "Entiendo que no puedes contactar al staff en este momento. No te preocupes, si el producto no fue entregado, "
                    "no se te cobrará. Si se realizó un cargo, será reembolsado automáticamente dentro de una semana. "
                    "Si no recibes el reembolso, por favor contacta a soporte al número +123456789."
                )
                user_state["step"] = "reassurance"
            elif "sí" in incoming_msg or "puedo" in incoming_msg:
                bot_response = (
                    "Perfecto, por favor informa al staff del club para que puedan resolver el problema. "
                    "Si necesitas algo más, no dudes en escribirme."
                )
                user_state["step"] = "final_step"
            else:
                bot_response = "¿Pudiste contactar al staff del club? Por favor, dime si necesitas ayuda adicional."

        # Paso 7: Confirmar Tranquilidad
        elif user_state["step"] == "reassurance":
            if "seguro" in incoming_msg or "¿seguro?" in incoming_msg:
                bot_response = (
                    "¡Por supuesto! Si el producto no fue entregado, no se te cobrará. Si tienes más dudas, no dudes en preguntarme."
                )
            else:
                bot_response = (
                    "Gracias por contactarnos. Espero que tu problema se resuelva pronto. "
                    "Si necesitas más ayuda, no dudes en escribirme. ¡Que tengas un buen día!"
                )
                user_state["step"] = "ask_name"

        # Guardar estado del usuario
        user_states[sender] = user_state

        # Enviar respuesta al usuario
        twilio_client.messages.create(
            body=bot_response,
            from_='whatsapp:+14155238886',
            to=sender
        )

    except Exception as e:
        print(f"Error: {e}")
