from fastapi import FastAPI, Request
from twilio.twiml.messaging_response import MessagingResponse
from twilio.rest import Client
from decouple import config

app = FastAPI()

# Configuración de Twilio
account_sid = config('TWILIO_ACCOUNT_SID')
auth_token = config('TWILIO_AUTH_TOKEN')
twilio_client = Client(account_sid, auth_token)

# Almacén temporal para guardar el estado del usuario
user_states = {}

@app.post("/webhook")
async def whatsapp_webhook(request: Request):
    try:
        # Leer los datos del mensaje entrante
        form = await request.form()
        incoming_msg = form.get("Body", "").strip()
        sender = form.get("From", "").strip()
        print(f"Mensaje recibido de {sender}: {incoming_msg}")

        # Recuperar el estado actual del usuario
        user_state = user_states.get(sender, {"step": "greeting", "name": ""})

        # Manejo del flujo
        if user_state["step"] == "greeting":
            # Saludo inicial y solicitud de nombre
            bot_response = "¡Hola! Soy el asistente de P-KAP. ¿Cómo te llamas?"
            user_states[sender] = {"step": "ask_name", "name": ""}

        elif user_state["step"] == "ask_name":
            # Guardar el nombre del usuario y pasar a las opciones principales
            user_state["name"] = incoming_msg
            bot_response = (
                f"Encantado de conocerte, {user_state['name']}. ¿En qué puedo ayudarte? Selecciona una opción:\n"
                "1️⃣ Pago\n"
                "2️⃣ Producto atascado\n"
                "3️⃣ Producto no entregado"
            )
            user_states[sender] = {"step": "main_menu", "name": user_state["name"]}

        elif user_state["step"] == "main_menu":
            # Manejo de la selección principal
            if incoming_msg == "1":
                bot_response = (
                    "Entendido. ¿Cuál es tu problema relacionado con el pago? Selecciona una opción:\n"
                    "1️⃣ No puedo pagar\n"
                    "2️⃣ Pagué y no se entregó el producto\n"
                    "3️⃣ El datáfono está apagado\n"
                    "4️⃣ El datáfono dice 'Fuera de servicio'"
                )
                user_states[sender] = {"step": "payment_issues", "name": user_state["name"]}
            elif incoming_msg == "2":
                bot_response = (
                    "Por favor, informa al staff del club sobre el producto atascado para que puedan ayudarte."
                )
                user_states[sender] = {"step": "done", "name": user_state["name"]}
            elif incoming_msg == "3":
                bot_response = (
                    "Primero quiero que te quedes tranquilo: si no se ha entregado el producto, no se te va a cobrar. "
                    "Puede que te figure el cargo, pero se te devolverá automáticamente. Dependiendo de tu entidad bancaria, "
                    "puede demorar de 3 a 5 días hábiles.\n\n"
                    "¿Ves algún producto caído? Selecciona una opción:\n"
                    "1️⃣ Sí\n"
                    "2️⃣ No"
                )
                user_states[sender] = {"step": "product_not_delivered", "name": user_state["name"]}
            else:
                bot_response = "Lo siento, no entendí tu respuesta. Por favor, selecciona una opción válida:\n1️⃣ Pago\n2️⃣ Producto atascado\n3️⃣ Producto no entregado."

        elif user_state["step"] == "payment_issues":
            if incoming_msg == "1":
                bot_response = "Entendido. Por favor, verifica que tengas saldo suficiente y vuelve a intentarlo."
                user_states[sender] = {"step": "done", "name": user_state["name"]}
            elif incoming_msg == "2":
                bot_response = (
                    "Primero quiero que te quedes tranquilo: si no se ha entregado el producto, no se te va a cobrar. "
                    "Puede que te figure el cargo, pero se te devolverá automáticamente. Dependiendo de tu entidad bancaria, "
                    "puede demorar de 3 a 5 días hábiles.\n\n"
                    "¿Ves algún producto caído? Selecciona una opción:\n"
                    "1️⃣ Sí\n"
                    "2️⃣ No"
                )
                user_states[sender] = {"step": "product_not_delivered", "name": user_state["name"]}
            elif incoming_msg == "3" or incoming_msg == "4":
                bot_response = (
                    "El datáfono podría necesitar un reinicio. Por favor, contacta al staff del club para asistencia.\n\n"
                    "¿Hay algo más en lo que pueda ayudarte? Selecciona una opción:\n1️⃣ Sí\n2️⃣ No"
                )
                user_states[sender] = {"step": "more_help", "name": user_state["name"]}
            else:
                bot_response = (
                    "Lo siento, no entendí tu respuesta. Por favor, selecciona una opción válida:\n"
                    "1️⃣ No puedo pagar\n"
                    "2️⃣ Pagué y no se entregó el producto\n"
                    "3️⃣ El datáfono está apagado\n"
                    "4️⃣ El datáfono dice 'Fuera de servicio'"
                )

        elif user_state["step"] == "product_not_delivered":
            if incoming_msg == "1":
                bot_response = (
                    "Por favor, ponte en contacto con el staff del club para resolver el problema del producto caído."
                )
                user_states[sender] = {"step": "done", "name": user_state["name"]}
            elif incoming_msg == "2":
                bot_response = "Puedes volver a intentar la compra. Si el problema persiste, contacta al staff del club."
                user_states[sender] = {"step": "done", "name": user_state["name"]}
            else:
                bot_response = "Lo siento, no entendí tu respuesta. Por favor, selecciona 1 para Sí o 2 para No."

        elif user_state["step"] == "done":
            bot_response = "¿Hay algo más en lo que pueda ayudarte? Selecciona una opción:\n1️⃣ Sí\n2️⃣ No"
            user_states[sender] = {"step": "more_help", "name": user_state["name"]}

        elif user_state["step"] == "more_help":
            # Regresar al menú principal si el usuario responde "Sí"
            if incoming_msg == "1":
                bot_response = (
                    f"Encantado de ayudarte de nuevo, {user_state['name']}. ¿En qué puedo ayudarte? Selecciona una opción:\n"
                    "1️⃣ Pago\n"
                    "2️⃣ Producto atascado\n"
                    "3️⃣ Producto no entregado"
                )
                user_states[sender] = {"step": "main_menu", "name": user_state["name"]}
            elif incoming_msg == "2":
                bot_response = f"¡Gracias por contactarnos, {user_state['name']}! Que tengas un excelente día."
                user_states[sender] = {"step": "greeting", "name": ""}
            else:
                bot_response = "Lo siento, no entendí tu respuesta. Por favor, selecciona 1 para Sí o 2 para No."

        # Enviar respuesta a través de Twilio
        message = twilio_client.messages.create(
            body=bot_response,
            from_='whatsapp:+14155238886',  # Número de WhatsApp de Twilio
            to=sender
        )
        print(f"Mensaje enviado a {sender}: {message.sid}")

        return str(MessagingResponse())

    except Exception as e:
        print(f"Error detallado: {str(e)}")
        return str(MessagingResponse().message("Lo siento, hubo un error procesando tu mensaje."))
