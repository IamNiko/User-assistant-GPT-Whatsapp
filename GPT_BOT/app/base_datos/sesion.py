from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.configuracion import configuracion

engine = create_engine(
    configuracion.URL_BASE_DATOS,
    connect_args={"check_same_thread": False}
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Mantener el nombre original para compatibilidad
obtener_db = get_db