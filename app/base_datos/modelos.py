from sqlalchemy import Column, Integer, String, Text
from sqlalchemy.ext.declarative import declarative_base
from pathlib import Path

# Base para definir modelos
Base = declarative_base()

# Modelo para guardar conversaciones
class Conversacion(Base):
    __tablename__ = "conversaciones"
    
    id = Column(Integer, primary_key=True, index=True)
    remitente = Column(String(100))
    mensaje = Column(Text)
    respuesta = Column(Text)