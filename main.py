from fastapi import FastAPI, Request, Form
from twilio.twiml.messaging_response import MessagingResponse
from twilio.rest import Client
from openai import OpenAI
from decouple import config

app = FastAPI()
account_sid = config('TWILIO_ACCOUNT_SID')
auth_token = config('TWILIO_AUTH_TOKEN')
twilio_client = Client(account_sid, auth_token)
openai_client = OpenAI(api_key=config("OPENAI_API_KEY"))
user_states = {}

@app.post("/webhook")
async def whatsapp_webhook(Body: str = Form(...), From: str = Form(...)):
   try:
       incoming_msg = Body.strip().replace("️⃣", "")
       sender = From.strip()
       user_state = user_states.get(sender, {"step": "ask_name", "name": None, "role": None})

       if user_state["step"] == "ask_name":
           bot_response = "¡Hola! Soy el asistente de P-KAP. ¿Cómo te llamas?"
           user_state["step"] = "welcome_user"

       elif user_state["step"] == "welcome_user":
           user_state["name"] = incoming_msg
           bot_response = f"¡Encantado de conocerte, {user_state['name']}!\n1️⃣ Jugador\n2️⃣ Staff del club"
           user_state["step"] = "identify_role"

       elif user_state["step"] == "identify_role":
           if incoming_msg in ["1", "1️⃣", "jugador", "Jugador"]:
               user_state["role"] = "Jugador"
               bot_response = f"¿Cuál es el problema?\n1️⃣ La máquina no dispensó el producto\n2️⃣ Producto atascado\n3️⃣ Problemas con el datáfono"
               user_state["step"] = "player_issue"
           elif incoming_msg in ["2", "2️⃣", "staff", "Staff"]:
               user_state["role"] = "Staff"
               bot_response = f"¿Qué necesitas revisar?\n1️⃣ Problemas de dispensación\n2️⃣ Datáfono\n3️⃣ Conexiones/Energía"
               user_state["step"] = "staff_issue"

       elif user_state["step"] == "staff_issue":
           if incoming_msg == "1":
               bot_response = ("Para problemas de dispensación, verifica:\n"
                             "1. ¿Hay productos atascados visibles?\n"
                             "2. ¿El mecanismo gira correctamente?\n"
                             "3. ¿Se escucha el motor?\n"
                             "Responde el número correspondiente")
               user_state["step"] = "staff_dispensing"
           elif incoming_msg == "2":
               bot_response = ("Revisión del datáfono:\n"
                             "1. Conexión eléctrica\n"
                             "2. Señal de red\n"
                             "3. Estado de la pantalla")
               user_state["step"] = "staff_dataphone"
           elif incoming_msg == "3":
               bot_response = ("Verifica en orden:\n"
                             "1. Cable de alimentación\n"
                             "2. Toma de corriente\n"
                             "3. Interruptor principal")
               user_state["step"] = "staff_connections"

       elif user_state["step"] == "staff_dispensing":
           staff_responses = {
               "1": "Si hay productos atascados:\n1. Apaga la máquina\n2. Retira con cuidado\n3. Verifica el mecanismo\n¿Necesitas más ayuda? (1: Sí, 2: No)",
               "2": "Si el mecanismo no gira:\n1. Verifica obstrucciones\n2. Revisa motor\n3. Comprueba conexiones\n¿Necesitas más ayuda? (1: Sí, 2: No)",
               "3": "Si no hay sonido del motor:\n1. Revisa alimentación\n2. Verifica fusibles\n3. Contacta soporte\n¿Necesitas más ayuda? (1: Sí, 2: No)"
           }
           bot_response = staff_responses.get(incoming_msg, "Respuesta no válida. Por favor selecciona 1, 2 o 3")
           user_state["step"] = "need_more_help"

       elif user_state["step"] == "staff_dataphone":
           staff_responses = {
               "1": "Para conexión eléctrica:\n1. Verifica cable\n2. Revisa toma\n3. Reinicia equipo\n¿Necesitas más ayuda? (1: Sí, 2: No)",
               "2": "Para señal de red:\n1. Verifica antena\n2. Comprueba cobertura\n3. Reinicia red\n¿Necesitas más ayuda? (1: Sí, 2: No)",
               "3": "Para pantalla:\n1. Revisa mensajes de error\n2. Verifica brillo\n3. Reinicia sistema\n¿Necesitas más ayuda? (1: Sí, 2: No)"
           }
           bot_response = staff_responses.get(incoming_msg, "Respuesta no válida. Por favor selecciona 1, 2 o 3")
           user_state["step"] = "need_more_help"

       elif user_state["step"] == "staff_connections":
           staff_responses = {
               "1": "Cable de alimentación:\n1. Verifica conexión\n2. Busca daños\n3. Prueba otro cable\n¿Necesitas más ayuda? (1: Sí, 2: No)",
               "2": "Toma de corriente:\n1. Prueba otro dispositivo\n2. Verifica voltaje\n3. Revisa fusibles\n¿Necesitas más ayuda? (1: Sí, 2: No)",
               "3": "Interruptor principal:\n1. Verifica posición\n2. Busca daños\n3. Prueba reinicio\n¿Necesitas más ayuda? (1: Sí, 2: No)"
           }
           bot_response = staff_responses.get(incoming_msg, "Respuesta no válida. Por favor selecciona 1, 2 o 3")
           user_state["step"] = "need_more_help"

       elif user_state["step"] == "player_issue":
           if incoming_msg == "1":
               bot_response = (f"{user_state['name']}, no te preocupes, si no recibiste el producto no se te cobrará. "
                             "¿Ves algún producto atascado?\n1️⃣ Sí\n2️⃣ No")
               user_state["step"] = "check_stuck"
           elif incoming_msg == "2":
               bot_response = "Por favor, notifica al staff del club sobre el producto atascado. ¿Necesitas algo más?\n1️⃣ Sí\n2️⃣ No"
               user_state["step"] = "need_more_help"
           elif incoming_msg == "3":
               bot_response = f"{user_state['name']}, ¿el datáfono está encendido y muestra señal?\n1️⃣ Sí\n2️⃣ No"
               user_state["step"] = "dataphone_check"

       elif user_state["step"] == "check_stuck":
           if incoming_msg == "1":
               bot_response = "Por favor, notifica al staff del club. No intentes sacarlo tú mismo. ¿Necesitas algo más?\n1️⃣ Sí\n2️⃣ No"
               user_state["step"] = "need_more_help"
           else:
               bot_response = "¿Intentaste hacer el pago?\n1️⃣ Sí\n2️⃣ No"
               user_state["step"] = "payment_attempt"

       elif user_state["step"] == "dataphone_check":
           if incoming_msg == "1":
               bot_response = "¿Has intentado realizar el pago?\n1️⃣ Sí, pero no funciona\n2️⃣ No he intentado"
               user_state["step"] = "payment_attempt"
           else:
               bot_response = "Por favor, notifica al staff que el datáfono está apagado/sin señal. ¿Necesitas algo más?\n1️⃣ Sí\n2️⃣ No"
               user_state["step"] = "need_more_help"

       elif user_state["step"] == "payment_attempt":
           if incoming_msg == "1":
               bot_response = ("No te preocupes, si el pago no funciona no se te cobrará. "
                             "Los cargos pendientes se cancelarán en 3-5 días según tu banco. "
                             "Por favor, notifica al staff. ¿Necesitas algo más?\n1️⃣ Sí\n2️⃣ No")
           else:
               bot_response = "Intenta el pago. Si no funciona, no te preocupes, no se te cobrará. ¿Necesitas algo más?\n1️⃣ Sí\n2️⃣ No"
           user_state["step"] = "need_more_help"

       elif user_state["step"] == "need_more_help":
           if incoming_msg in ["1", "1️⃣"]:
               if user_state["role"] == "Jugador":
                   bot_response = f"¿Cuál es el problema?\n1️⃣ La máquina no dispensó el producto\n2️⃣ Producto atascado\n3️⃣ Problemas con el datáfono"
                   user_state["step"] = "player_issue"
               else:
                   bot_response = f"¿Qué necesitas revisar?\n1️⃣ Problemas de dispensación\n2️⃣ Datáfono\n3️⃣ Conexiones/Energía"
                   user_state["step"] = "staff_issue"
           else:
               bot_response = f"¡Gracias por contactarnos, {user_state['name']}! Que tengas un excelente día."
               user_state = {"step": "ask_name", "name": None, "role": None}

       user_states[sender] = user_state
       twilio_client.messages.create(
           body=bot_response,
           from_='whatsapp:+14155238886',
           to=sender
       )
       return str(MessagingResponse())

   except Exception as e:
       print(f"Error: {e}")
       return str(MessagingResponse().message("Error en el sistema"))