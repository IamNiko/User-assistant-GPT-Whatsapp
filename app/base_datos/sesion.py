from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.configuracion import configuracion
from app.base_datos.modelos import Base
from pathlib import Path

# Asegurar que el directorio existe
Path(configuracion.DB_DIR).mkdir(parents=True, exist_ok=True)

# Motor de la base de datos
engine = create_engine(
    configuracion.URL_BASE_DATOS,
    connect_args={"check_same_thread": False}
)

# Crear todas las tablas
Base.metadata.create_all(bind=engine)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def obtener_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()