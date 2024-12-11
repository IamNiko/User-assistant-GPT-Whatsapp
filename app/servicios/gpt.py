import time
from openai import OpenAI
from app.configuracion import configuracion
from typing import Dict, Any
from sqlalchemy.orm import Session
from app.base_datos.modelos import Conversacion
from app.servicios.prompts import gestor_prompts

cliente = OpenAI(api_key=configuracion.OPENAI_API_KEY)

def obtener_respuesta_gpt4(mensaje: str, contexto: Dict[str, Any], db: Session) -> str:
    tiempo_inicio = time.time()
    
    try:
        print(f"Iniciando procesamiento de mensaje: {mensaje[:50]}...")
        
        # Medir tiempo de selección de prompt
        t_prompt_inicio = time.time()
        if contexto.get("rol") == "tecnico" and contexto.get("acceso_tecnico"):
            prompt_sistema = gestor_prompts.obtener_prompt('tecnico')
        elif contexto.get("rol") == "staff":
            prompt_sistema = gestor_prompts.obtener_prompt('staff')
        elif contexto.get("rol") == "jugador":
            prompt_sistema = gestor_prompts.obtener_prompt('jugador')
        else:
            prompt_sistema = gestor_prompts.obtener_prompt('base')
        print(f"Tiempo selección prompt: {time.time() - t_prompt_inicio:.2f} segundos")
            
        # Medir tiempo de preparación de mensajes
        t_prep_inicio = time.time()
        mensajes = [
            {"role": "system", "content": prompt_sistema},
            {"role": "user", "content": mensaje}
        ]

        if contexto.get("nombre"):
            mensajes.insert(1, {
                "role": "system",
                "content": f"El usuario se llama {contexto['nombre']}. Dirígete a él por su nombre."
            })
        print(f"Tiempo preparación mensajes: {time.time() - t_prep_inicio:.2f} segundos")

        # Medir tiempo de acceso a BD
        t_bd_inicio = time.time()
        try:
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
            print(f"Tiempo acceso BD: {time.time() - t_bd_inicio:.2f} segundos")
        except Exception as db_error:
            print(f"Error al obtener historial: {db_error}")

        # Medir tiempo de llamada a GPT
        t_gpt_inicio = time.time()
        respuesta = cliente.chat.completions.create(
            model="gpt-4",
            messages=mensajes
        )
        tiempo_gpt = time.time() - t_gpt_inicio
        print(f"Tiempo llamada GPT: {tiempo_gpt:.2f} segundos")
        
        tiempo_total = time.time() - tiempo_inicio
        print(f"Tiempo total de procesamiento: {tiempo_total:.2f} segundos")
        
        return respuesta.choices[0].message.content
        
    except Exception as e:
        print(f"Error GPT-4: {e}")
        return f"Lo siento {contexto.get('nombre', '')}, ¿podrías reformular tu pregunta?"