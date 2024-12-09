import os
from dotenv import load_dotenv

# Cargar variables de entorno desde .env
load_dotenv()

class Configuracion:
    # API Keys
    OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
    TWILIO_ACCOUNT_SID = os.getenv('TWILIO_ACCOUNT_SID')
    TWILIO_AUTH_TOKEN = os.getenv('TWILIO_AUTH_TOKEN')
    CLAVE_TECNICA = os.getenv('TECH_ACCESS_KEY')
    
    # Configuración de Twilio
    NUMERO_TWILIO = 'whatsapp:+14155238886'
    
    # Configuración de Base de Datos
    URL_BASE_DATOS = "sqlite:///./database.db"
    
    # Configuración de Mensajes
    LONGITUD_MAXIMA_MENSAJE = 1500

configuracion = Configuracion()