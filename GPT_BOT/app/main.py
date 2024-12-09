import sys
import os
from pathlib import Path
from dotenv import load_dotenv
import re

# Configurar rutas y variables de entorno
root_dir = Path(__file__).resolve().parent.parent
sys.path.append(str(root_dir))

# Cargar variables de entorno
load_dotenv()

from fastapi import FastAPI, Form, HTTPException, Depends
from app.nucleo.estados import gestor_estados
from app.servicios.gpt import obtener_respuesta_gpt4
from app.servicios.twilio import enviar_mensaje
from app.servicios.mensajes import dividir_mensaje
from app.base_datos.sesion import obtener_db
from app.servicios.prompts import gestor_prompts
from app.nucleo.validadores import es_nombre_valido, limpiar_nombre, detectar_rol  # Cambiado a los nombres en español
from sqlalchemy.orm import Session
from app.base_datos.modelos import Conversacion
from typing import Dict, Any

app = FastAPI()

# Usar os.getenv en lugar de config
TECH_ACCESS_KEY = os.getenv('TECH_ACCESS_KEY', '1234')

# Función auxiliar para obtener el prompt según el rol
def obtener_prompt_por_rol(rol: str) -> str:
    if rol == "jugador":
        return gestor_prompts.obtener_prompt('jugador')
    elif rol == "staff":
        return gestor_prompts.obtener_prompt('staff')
    elif rol == "tecnico":
        return gestor_prompts.obtener_prompt('tecnico')
    return gestor_prompts.obtener_prompt('base')

@app.post("/webhook")
async def webhook_whatsapp(
    Body: str = Form(...),
    From: str = Form(...),
    db: Session = Depends(obtener_db)
):
    print(f"Solicitud recibida. Body: {Body}, From: {From}")

    try:
        mensaje_entrante = Body.strip()
        remitente = From.strip()
        estado_usuario = gestor_estados.obtener_estado(remitente)

        # FLUJO DE INICIO
        if estado_usuario["paso"] == "inicio":
            gestor_estados.actualizar_estado(remitente, estado_usuario)
            respuesta_bot = "¡Hola! Soy el asistente de P-KAP. ¿Podrías decirme tu nombre?"
            estado_usuario["paso"] = "nombre"
            gestor_estados.actualizar_estado(remitente, estado_usuario)

        # FLUJO DE NOMBRE
        elif estado_usuario["paso"] == "nombre":
            gestor_estados.actualizar_estado(remitente, estado_usuario)
            if estado_usuario.get("nombre"):
                respuesta_bot = (
                    f"¡Gracias {estado_usuario['nombre']}! ¿Eres jugador, personal del club o servicio técnico?\n"
                    "1️⃣ Jugador\n"
                    "2️⃣ Staff\n"
                    "3️⃣ Servicio Técnico"
                )
                estado_usuario["paso"] = "rol"
                gestor_estados.actualizar_estado(remitente, estado_usuario)
            elif not es_nombre_valido(mensaje_entrante):
                if "llamo" in mensaje_entrante.lower() and "paquete" in mensaje_entrante.lower():
                    estado_usuario["nombre"] = "paquete"
                    respuesta_bot = (
                        f"¡Gracias paquete! ¿Eres jugador, personal del club o servicio técnico?\n"
                        "1️⃣ Jugador\n"
                        "2️⃣ Staff\n"
                        "3️⃣ Servicio Técnico"
                    )
                    estado_usuario["paso"] = "rol"
                    gestor_estados.actualizar_estado(remitente, estado_usuario)
                elif any(palabra in mensaje_entrante.lower() for palabra in ["por que", "para que", "porque", "?", "que"]):
                    respuesta_bot = (
                        "Entiendo tu pregunta. Solo necesito tu nombre para poder darte un trato más personalizado "
                        "y amigable. No necesito tu nombre completo, solo un nombre por el cual pueda llamarte. "
                        "Tu privacidad es importante y esta información solo se usa para nuestra conversación. "
                        "Si prefieres, puedes decirme cómo te gustaría que te llame."
                    )
                else:
                    prompt_especial = f"El usuario respondió '{mensaje_entrante}' cuando le pedí su nombre. Da una respuesta empática y amable explicando por qué necesitas su nombre real."
                    respuesta_bot = obtener_respuesta_gpt4(prompt_especial, estado_usuario, db)
            else:
                estado_usuario["nombre"] = limpiar_nombre(mensaje_entrante)
                respuesta_bot = (
                    f"¡Gracias {estado_usuario['nombre']}! ¿Eres jugador, personal del club o servicio técnico?\n"
                    "1️⃣ Jugador\n"
                    "2️⃣ Staff\n"
                    "3️⃣ Servicio Técnico"
                )
                estado_usuario["paso"] = "rol"
                gestor_estados.actualizar_estado(remitente, estado_usuario)

        # FLUJO DE ROL
        elif estado_usuario["paso"] == "rol":
            gestor_estados.actualizar_estado(remitente, estado_usuario)
            rol = detectar_rol(mensaje_entrante)
            if rol:
                estado_usuario["rol"] = rol
                if rol == "jugador":
                    respuesta_bot = (
                        f"¿En qué puedo ayudarte {estado_usuario['nombre']}?\n"
                        "1️⃣ Problema con la entrega de un producto\n"
                        "2️⃣ Problema con el pago\n"
                        "3️⃣ Problema con la máquina\n"
                        "4️⃣ Otras consultas"
                    )
                    estado_usuario["paso"] = "problema"
                    gestor_estados.actualizar_estado(remitente, estado_usuario)
                elif rol == "staff":
                    respuesta_bot = (
                        f"¿Qué tipo de problema necesitas resolver {estado_usuario['nombre']}?\n"
                        "1️⃣ Producto caído o atascado\n"
                        "2️⃣ Problema con datáfono/pagos\n"
                        "3️⃣ Necesito reiniciar la máquina\n"
                        "4️⃣ Otro problema"
                    )
                    estado_usuario["paso"] = "problema"
                    gestor_estados.actualizar_estado(remitente, estado_usuario)
                else:  # técnico
                    respuesta_bot = "Por favor, introduce la clave de acceso técnico:"
                    estado_usuario["paso"] = "validacion_tecnica"
                    gestor_estados.actualizar_estado(remitente, estado_usuario)
            else:
                respuesta_bot = "Por favor indica si eres jugador (1), staff (2) o servicio técnico (3)"

        # FLUJO DE PROBLEMA
        elif estado_usuario["paso"] == "problema":
            gestor_estados.actualizar_estado(remitente, estado_usuario)
            if estado_usuario["rol"] == "jugador":
                if mensaje_entrante == "1":  # Problema con entrega
                    respuesta_bot = (
                        "¡Entendido! ¿Qué problema estás experimentando exactamente?\n"
                        "1️⃣ El producto que quería no se entregó\n"
                        "2️⃣ Pagué, pero no recibí nada\n"
                        "3️⃣ Veo un producto atascado/caído en la máquina\n"
                        "4️⃣ Otro problema con la entrega de un producto"
                    )
                    estado_usuario["paso"] = "detalle_problema"
                elif mensaje_entrante == "2":  # Problema con pago
                    respuesta_bot = (
                        "Lo siento por el inconveniente con el pago. Por favor, indícame más detalles:\n"
                        "1️⃣ Pagué pero no recibí el producto\n"
                        "2️⃣ No aparece el cargo en mi cuenta\n"
                        "3️⃣ Otro problema relacionado con el pago"
                    )
                    estado_usuario["paso"] = "detalle_pago"
                elif mensaje_entrante == "3":  # Problema con máquina
                    respuesta_bot = (
                        "Gracias por informarlo. Por favor, selecciona la descripción que mejor se ajuste:\n"
                        "1️⃣ La máquina no responde\n"
                        "2️⃣ Las luces no funcionan\n"
                        "3️⃣ El sistema de pago no funciona\n"
                        "4️⃣ Otro problema técnico con la máquina"
                    )
                    estado_usuario["paso"] = "detalle_maquina"
                elif mensaje_entrante == "4":  # Otras consultas
                    respuesta_bot = (
                        "¡Entendido! Por favor, indícame cómo puedo ayudarte:\n"
                        "1️⃣ Información sobre el funcionamiento de la máquina\n"
                        "2️⃣ Consultar políticas de reembolso\n"
                        "3️⃣ Contactar con soporte técnico\n"
                        "4️⃣ Otro tipo de consulta"
                    )
                    estado_usuario["paso"] = "detalle_otros"
            elif estado_usuario["rol"] == "staff":
                if mensaje_entrante == "1":  # Producto atascado
                    respuesta_bot = obtener_respuesta_gpt4(
                        "Un miembro del staff reporta un producto atascado. Proporciona instrucciones paso a paso.",
                        estado_usuario,
                        db
                    )
                    estado_usuario["paso"] = "detalle_staff"
                elif mensaje_entrante == "2":  # Problema pagos
                    respuesta_bot = obtener_respuesta_gpt4(
                        "Un miembro del staff reporta problemas con el datáfono/pagos. Proporciona instrucciones.",
                        estado_usuario,
                        db
                    )
                    estado_usuario["paso"] = "detalle_staff"
                elif mensaje_entrante == "3":  # Reinicio máquina
                    respuesta_bot = obtener_respuesta_gpt4(
                        "Un miembro del staff necesita reiniciar la máquina. Proporciona el procedimiento seguro.",
                        estado_usuario,
                        db
                    )
                    estado_usuario["paso"] = "detalle_staff"
                elif mensaje_entrante == "4":  # Otro problema
                    respuesta_bot = "Por favor, describe el problema que estás experimentando:"
                    estado_usuario["paso"] = "detalle_staff"

            gestor_estados.actualizar_estado(remitente, estado_usuario)

        # VALIDACIÓN TÉCNICA
        elif estado_usuario["paso"] == "validacion_tecnica":
            gestor_estados.actualizar_estado(remitente, estado_usuario)
            if mensaje_entrante == TECH_ACCESS_KEY:
                estado_usuario["acceso_tecnico"] = True
                respuesta_bot = (
                    "⚠️ ACCESO TÉCNICO CONCEDIDO ⚠️\n\n"
                    "PROCEDIMIENTO DE ACCESO AL SISTEMA:\n\n"
                    "ACCESO FÍSICO:\n"
                    "1. Localizar cofre en frente de máquina\n"
                    "2. Ingresar código: 7527\n"
                    "3. Retirar la llave\n"
                    "4. Insertar llave en cerradura\n"
                    "5. Tirar del panel para abrir\n\n"
                    "ACCESO AL SISTEMA:\n"
                    "1. En tablet, presionar 'admin'\n"
                    "2. Pulsar cuadro blanco para teclado\n"
                    "3. Cambiar a teclado numérico\n"
                    "4. Ingresar: 123456\n\n"
                    "Una vez dentro, ¿qué necesitas consultar?\n"
                    "1️⃣ Diagnóstico de errores\n"
                    "2️⃣ Configuración de sistema\n"
                    "3️⃣ Mantenimiento preventivo\n"
                    "4️⃣ Calibración de componentes"
                )
                estado_usuario["paso"] = "menu_tecnico"
                gestor_estados.actualizar_estado(remitente, estado_usuario)
            else:
                respuesta_bot = "Clave incorrecta. Por favor, intenta de nuevo o contacta a soporte."

        # MENÚ TÉCNICO
        elif estado_usuario["paso"] == "menu_tecnico":
            if not estado_usuario.get("acceso_tecnico"):
                respuesta_bot = "No tienes acceso técnico validado. Por favor, introduce la clave de acceso."
                estado_usuario["paso"] = "validacion_tecnica"
            else:
                if mensaje_entrante == "1":  # Diagnóstico
                    respuesta_bot = (
                        "Diagnóstico de errores. Por favor, indícame:\n"
                        "1️⃣ Código de error específico (ej: E001)\n"
                        "2️⃣ Descripción del problema\n"
                        "3️⃣ Consultar lista de errores\n"
                        "4️⃣ Volver al menú principal"
                    )
                    estado_usuario["paso"] = "diagnostico_errores"
                elif mensaje_entrante == "2":  # Configuración
                    respuesta_bot = (
                        "Configuración de sistema. Selecciona:\n"
                        "1️⃣ Ajustes de motor\n"
                        "2️⃣ Parámetros de sensores\n"
                        "3️⃣ Configuración de dispensador\n"
                        "4️⃣ Volver al menú principal"
                    )
                    estado_usuario["paso"] = "config_sistema"
                elif mensaje_entrante == "3":  # Mantenimiento
                    respuesta_bot = (
                        "Mantenimiento preventivo:\n"
                        "1️⃣ Procedimientos diarios\n"
                        "2️⃣ Procedimientos semanales\n"
                        "3️⃣ Procedimientos mensuales\n"
                        "4️⃣ Volver al menú principal"
                    )
                    estado_usuario["paso"] = "mantenimiento"
                elif mensaje_entrante == "4":  # Calibración
                    respuesta_bot = (
                        "Calibración de componentes:\n"
                        "1️⃣ Calibración de posicionamiento\n"
                        "2️⃣ Ajuste de sensores\n"
                        "3️⃣ Calibración de motores\n"
                        "4️⃣ Volver al menú principal"
                    )
                    estado_usuario["paso"] = "calibracion"
                else:
                    respuesta_bot = obtener_respuesta_gpt4(mensaje_entrante, estado_usuario, db)

            gestor_estados.actualizar_estado(remitente, estado_usuario)

        # MENÚS TÉCNICOS ESPECÍFICOS

        elif estado_usuario["paso"] in ["diagnostico_errores", "config_sistema", "mantenimiento", "calibracion"]:
            if mensaje_entrante.lower() in ["ver acceso", "procedimiento", "como accedo", "acceso"]:
                respuesta_bot = (
                    "📋 PROCEDIMIENTO DE ACCESO AL SISTEMA 📋\n\n"
                    "ACCESO FÍSICO:\n"
                    "1. Localizar cofre en frente de máquina\n"
                    "2. Ingresar código: 7527\n"
                    "3. Retirar la llave\n"
                    "4. Insertar llave en cerradura\n"
                    "5. Tirar del panel para abrir\n\n"
                    "ACCESO AL SISTEMA:\n"
                    "1. En tablet, presionar 'admin'\n"
                    "2. Pulsar cuadro blanco para teclado\n"
                    "3. Cambiar a teclado numérico\n"
                    "4. Ingresar: 123456\n\n"
                    "¿Deseas continuar con tu consulta anterior?"
                )
            elif mensaje_entrante == "4":  # Volver al menú principal
                respuesta_bot = (
                    f"¿Qué necesitas consultar {estado_usuario['nombre']}?\n"
                    "1️⃣ Diagnóstico de errores\n"
                    "2️⃣ Configuración de sistema\n"
                    "3️⃣ Mantenimiento preventivo\n"
                    "4️⃣ Calibración de componentes"
                )
                estado_usuario["paso"] = "menu_tecnico"
            else:
                if estado_usuario["paso"] == "diagnostico_errores":
                    if mensaje_entrante.upper().startswith('E'):
                        content = f"Proporciona información técnica detallada sobre el error {mensaje_entrante}"
                    else:
                        content = f"Como técnico, necesito información sobre: {mensaje_entrante}"
                else:
                    content = f"Como técnico, necesito información sobre la opción {mensaje_entrante} del menú {estado_usuario['paso']}"
                
                if "historial_conversacion" not in estado_usuario:
                    estado_usuario["historial_conversacion"] = []
                
                estado_usuario["historial_conversacion"].append({"role": "user", "content": content})
                respuesta_bot = obtener_respuesta_gpt4(content, estado_usuario, db)
                estado_usuario["historial_conversacion"].append({"role": "assistant", "content": respuesta_bot})

        # DETALLES DE PROBLEMAS (JUGADOR/STAFF)
        elif estado_usuario["paso"] in ["detalle_problema", "detalle_pago", "detalle_maquina", "detalle_otros", "detalle_staff"]:
            # Verificar si el usuario ha pagado
            if re.search(r"(?:he|ya)\s+(?:pagado|comprado)|hice\s+(?:el\s+)?pago|si|exacto|efectivamente|claro", mensaje_entrante.lower()):
                estado_usuario["ha_pagado"] = True
            
            elif estado_usuario["paso"] == "detalle_otros":
                if mensaje_entrante == "1":  # Información sobre funcionamiento
                    respuesta_bot = (
                        f"Te explico cómo funciona nuestra máquina, {estado_usuario['nombre']}:\n\n"
                        "1. Selección:\n"
                        "   • Elige tu producto en la pantalla táctil\n"
                        "   • Verás el precio claramente mostrado\n\n"
                        "2. Pago:\n"
                        "   • Presiona el botón verde del datáfono\n"
                        "   • Métodos aceptados:\n"
                        "     ✓ Tarjeta bancaria\n"
                        "     ✓ Contactless\n"
                        "     ✓ Código QR\n"
                        "     ❌ No se acepta efectivo\n\n"
                        "3. Recogida:\n"
                        "   • Espera que el producto caiga\n"
                        "   • Recógelo de la bandeja inferior\n\n"
                        "¿Necesitas que te aclare algún paso?"
                    )
            elif mensaje_entrante == "2":
                content = (
                    f"El usuario {estado_usuario['nombre']} pregunta sobre políticas de reembolso. "
                    "Explica el proceso de devolución automática y los tiempos esperados."
                )
            elif mensaje_entrante == "3":
                content = (
                    f"El usuario {estado_usuario['nombre']} necesita contactar con soporte. "
                    "Proporciona la información de contacto y los canales disponibles."
                )
            elif mensaje_entrante == "4":
                content = (
                    f"El usuario {estado_usuario['nombre']} tiene otra consulta. "
                    "Pregúntale en qué puedes ayudarle."
                )
            else:
                content = (
                    f"El usuario {estado_usuario['nombre']} dice: {mensaje_entrante}\n"
                    "Responde su consulta de manera amable y detallada."
                )

            try:
                respuesta_bot = obtener_respuesta_gpt4(content, estado_usuario, db)
                if "Lo siento" in respuesta_bot and "reformular" in respuesta_bot:
                    # Si obtuvimos la respuesta de error por defecto, intentamos una respuesta más genérica
                    respuesta_bot = (
                        f"Te explico cómo funciona nuestra máquina, {estado_usuario['nombre']}:\n\n"
                        "1. La máquina tiene una pantalla táctil donde puedes ver todos los productos\n"
                        "2. Selecciona el producto que desees\n"
                        "3. Realiza el pago con tarjeta, contactless o QR\n"
                        "4. Recoge tu producto de la bandeja\n\n"
                        "¿Hay algo específico que quieras saber sobre el funcionamiento?"
                    )
            except Exception as e:
                print(f"Error al obtener respuesta GPT: {e}")
                respuesta_bot = (
                    f"Disculpa {estado_usuario['nombre']}, estoy teniendo problemas técnicos. "
                    "¿Podrías intentarlo de nuevo en unos momentos?"
                )
            
            if "club" in mensaje_entrante.lower() or "personal" in mensaje_entrante.lower() or "alguien" in mensaje_entrante.lower():
                content = "El usuario pregunta sobre buscar personal del club para ayuda. Como jugador que ya pagó, ¿qué debería responderle?"
            else:
                content = mensaje_entrante
            
            estado_usuario["historial_conversacion"].append({"role": "user", "content": content})
            respuesta_bot = obtener_respuesta_gpt4(content, estado_usuario, db)
            estado_usuario["historial_conversacion"].append({"role": "assistant", "content": respuesta_bot})

        # CONVERSACIÓN GENERAL
        else:
            if re.search(r"(?:he|ya)\s+(?:pagado|comprado)|hice\s+(?:el\s+)?pago|si|exacto|efectivamente|claro", mensaje_entrante.lower()):
                estado_usuario["ha_pagado"] = True
            
            estado_usuario["historial_conversacion"].append({"role": "user", "content": mensaje_entrante})
            respuesta_bot = obtener_respuesta_gpt4(mensaje_entrante, estado_usuario, db)
            estado_usuario["historial_conversacion"].append({"role": "assistant", "content": respuesta_bot})

        # Actualizar estado y guardar en base de datos
        gestor_estados.actualizar_estado(remitente, estado_usuario)
        
        try:
                    conversacion = Conversacion(
                        remitente=remitente,
                        mensaje=mensaje_entrante,
                        respuesta=respuesta_bot
                    )
                    db.add(conversacion)
                    db.commit()
        except Exception as db_error:
            print(f"Error al guardar en la base de datos: {db_error}")
            db.rollback()
            # Continuar con el envío del mensaje aunque falle la BD
                
        # Dividir y enviar mensajes largos
        partes_mensaje = dividir_mensaje(respuesta_bot)
        for parte in partes_mensaje:
            enviar_mensaje(remitente, parte)  # Quitamos el await
        
        return {"status": "success"}
        
    except Exception as e:
        print(f"Error general: {e}")
        db.rollback()
        # En caso de error, al menos intentar enviar un mensaje al usuario
        try:
            enviar_mensaje(  # Quitamos el await
                remitente,
                "Lo siento, ocurrió un error. Por favor, intenta nuevamente."
            )
        except:
            pass
        raise HTTPException(status_code=500, detail=str(e))

        
    except Exception as e:
        print(f"Error: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
