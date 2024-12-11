from typing import Dict, Tuple
from app.nucleo.estados import gestor_estados
from app.servicios.gpt import obtener_respuesta_gpt4
from app.nucleo.validadores import es_nombre_valido, limpiar_nombre, detectar_rol
from sqlalchemy.orm import Session

class ManejadorConversacion:
    def __init__(self):
        self.respuestas_menu = {
            "inicio": "¡Hola! Soy el asistente de P-KAP. ¿Podrías decirme tu nombre?",
            "roles": (
                "¿Eres jugador, personal del club o servicio técnico?\n"
                "1️⃣ Jugador\n"
                "2️⃣ Staff\n"
                "3️⃣ Servicio Técnico"
            ),
            "menu_jugador": (
                "¿En qué puedo ayudarte?\n"
                "1️⃣ Problema con la entrega\n"
                "2️⃣ Problema con el pago\n"
                "3️⃣ Problema con la máquina\n"
                "4️⃣ Otro"
            ),
            "menu_staff": (
                "¿Qué tipo de problema necesitas resolver?\n"
                "1️⃣ Producto atascado\n"
                "2️⃣ Problema con pagos\n"
                "3️⃣ Reiniciar máquina\n"
                "4️⃣ Otro problema"
            )
        }

    async def procesar_mensaje(
        self, 
        mensaje: str, 
        remitente: str, 
        db: Session
    ) -> Tuple[str, Dict]:
        estado = gestor_estados.obtener_estado(remitente)
        
        if estado["paso"] == "inicio":
            return self._procesar_inicio(estado)
            
        elif estado["paso"] == "nombre":
            return self._procesar_nombre(mensaje, estado, db)
            
        elif estado["paso"] == "rol":
            return self._procesar_rol(mensaje, estado)
            
        elif estado["paso"] == "problema":
            return self._procesar_problema(mensaje, estado)
            
        elif estado["paso"] == "validacion_tecnica":
            return self._procesar_validacion_tecnica(mensaje, estado)
            
        # Procesar otros estados según sea necesario
        return self._procesar_conversacion_general(mensaje, estado, db)

    def _procesar_inicio(self, estado: Dict) -> Tuple[str, Dict]:
        estado["paso"] = "nombre"
        return self.respuestas_menu["inicio"], estado

    def _procesar_nombre(self, mensaje: str, estado: Dict, db: Session) -> Tuple[str, Dict]:
        if es_nombre_valido(mensaje):
            estado["nombre"] = limpiar_nombre(mensaje)
            estado["paso"] = "rol"
            return f"¡Gracias {estado['nombre']}! {self.respuestas_menu['roles']}", estado
        else:
            return obtener_respuesta_gpt4(
                f"El usuario respondió '{mensaje}' cuando le pedí su nombre. Por favor responde de forma empática.",
                estado,
                db
            ), estado

    def _procesar_rol(self, mensaje: str, estado: Dict) -> Tuple[str, Dict]:
        rol = detectar_rol(mensaje)
        if rol:
            estado["rol"] = rol
            estado["paso"] = "problema"
            if rol == "jugador":
                return self.respuestas_menu["menu_jugador"], estado
            elif rol == "staff":
                return self.respuestas_menu["menu_staff"], estado
            else:
                return "Introduce la clave de acceso técnico:", estado
        return "Por favor indica si eres jugador (1), staff (2) o servicio técnico (3).", estado
    


manejador_conversacion = ManejadorConversacion()