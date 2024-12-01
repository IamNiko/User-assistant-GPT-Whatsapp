from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.orm import declarative_base, sessionmaker

# Configuración de la base de datos SQLite
DATABASE_URL = "sqlite:///./database.db"

# Motor de la base de datos
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})

# Sesión para interactuar con la base de datos
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base para definir modelos
Base = declarative_base()

# Modelo de ejemplo para guardar conversaciones
class Conversation(Base):
    __tablename__ = "conversations"
    id = Column(Integer, primary_key=True, index=True)
    sender = Column(String)
    message = Column(String)
    response = Column(String)

# Crear las tablas en la base de datos
Base.metadata.create_all(bind=engine)
