from sqlalchemy import create_engine, Column, Integer, String, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# Configuración de la base de datos SQLite
DATABASE_URL = "sqlite:///./database.db"

# Motor de la base de datos
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False}
)

# Sesión para interactuar con la base de datos
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base para definir modelos
Base = declarative_base()

# Modelo para guardar conversaciones
class Conversacion(Base):
    __tablename__ = "conversaciones"
    
    id = Column(Integer, primary_key=True, index=True)
    remitente = Column(String(100))
    mensaje = Column(Text)
    respuesta = Column(Text)

# Crear todas las tablas en la base de datos
def init_db():
    Base.metadata.create_all(bind=engine)

# Crear las tablas al importar el módulo
init_db()