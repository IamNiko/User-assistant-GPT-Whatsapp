from openai import OpenAI
from app.configuracion import configuracion
from typing import Dict, Any
from sqlalchemy.orm import Session
from app.base_datos.modelos import Conversacion  # Añadimos esta importación
from app.servicios.prompts import gestor_prompts

cliente = OpenAI(api_key=configuracion.OPENAI_API_KEY)

def obtener_respuesta_gpt4(mensaje: str, contexto: Dict[str, Any], db: Session) -> str:
    try:
        # Obtener el prompt adecuado según el rol del usuario
        if contexto.get("rol") == "tecnico" and contexto.get("acceso_tecnico"):
            prompt_sistema = gestor_prompts.obtener_prompt('tecnico')
        elif contexto.get("rol") == "staff":
            prompt_sistema = gestor_prompts.obtener_prompt('staff')
        elif contexto.get("rol") == "jugador":
            prompt_sistema = gestor_prompts.obtener_prompt('jugador')
        else:
            prompt_sistema = gestor_prompts.obtener_prompt('base')
            
        # Crear el mensaje inicial
        mensajes = [
            {"role": "system", "content": prompt_sistema},
            {"role": "user", "content": mensaje}
        ]

        # Agregar contexto relevante
        if contexto.get("nombre"):
            mensajes.insert(1, {
                "role": "system",
                "content": f"El usuario se llama {contexto['nombre']}. Dirígete a él por su nombre."
            })

        try:
            # Intentar obtener el historial de conversación
            conversaciones_recientes = (
                db.query(Conversacion)
                .filter(Conversacion.remitente == contexto.get("remitente"))
                .order_by(Conversacion.id.desc())
                .limit(3)
                .all()
            )

            for conv in reversed(conversaciones_recientes):
                mensajes.extend([
                    {"role": "user", "content": conv.mensaje},
                    {"role": "assistant", "content": conv.respuesta}
                ])
        except Exception as db_error:
            print(f"Error al obtener historial: {db_error}")
            # Continuar sin el historial si hay error

        # Obtener respuesta de GPT-4
        respuesta = cliente.chat.completions.create(
            model="gpt-4",
            messages=mensajes
        )
        
        return respuesta.choices[0].message.content
        
    except Exception as e:
        print(f"Error GPT-4: {e}")
        return f"Lo siento {contexto.get('nombre', '')}, ¿podrías reformular tu pregunta?"