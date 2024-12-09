from twilio.rest import Client
from app.configuracion import configuracion

client = Client(
    configuracion.TWILIO_ACCOUNT_SID,
    configuracion.TWILIO_AUTH_TOKEN
)

def enviar_mensaje(destinatario: str, mensaje: str) -> None:
    """
    Envía un mensaje a través de Twilio de forma síncrona.
    """
    return client.messages.create(
        body=mensaje,
        from_=configuracion.NUMERO_TWILIO,
        to=destinatario
    )