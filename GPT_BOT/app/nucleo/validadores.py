import re
from typing import List

def es_nombre_valido(mensaje: str) -> bool:
    """
    Verifica si un nombre es válido según criterios específicos.
    
    Un nombre válido no debe contener palabras comunes o genéricas, ser demasiado largo,
    contener caracteres especiales o números, ni ser una pregunta o prueba.

    Args:
        mensaje (str): El nombre a validar.

    Returns:
        bool: True si el nombre es válido, False en caso contrario.
    """
    # Conjunto de palabras consideradas inválidas para un nombre
    palabras_invalidas: set = {
        'ok', 'vale', 'bien', 'bueno', 'si', 'no', 'hola', 
        'para', 'por', 'que', 'cual', 'como', 'cuando',
        'porque', 'nose', 'nose', 'nop', 'yes', 'yeah',
        'claro', 'dale', 'obvio', 'test', 'prueba',
        'entendido', 'entendi', 'comprendo', 'comprendido',
        'ya', 'te', 'he', 'dicho', 'dije'
    }
    
    # Convertir el mensaje a minúsculas y eliminar espacios en blanco
    texto = mensaje.lower().strip()
    palabras = texto.split()
    
    # Verificar si el texto está vacío o contiene palabras inválidas
    if len(palabras) == 0 or any(palabra in palabras_invalidas for palabra in palabras):
        return False
    
    # Verificar si el texto excede la longitud máxima permitida
    if len(texto) > 20:
        return False
        
    # Verificar si el texto contiene caracteres especiales o números
    if re.search(r'[0-9@#$%^&*(),.?":{}|<>]', texto):
        return False
        
    # Verificar si el texto contiene frases o caracteres específicos no permitidos
    if any(x in texto for x in ['porque', 'para que', 'por que', '?', '!', 'jaja', 'test']):
        return False
        
    # Verificar si el texto contiene al menos dos letras válidas
    if len(re.sub(r'[^a-zA-ZáéíóúñÁÉÍÓÚÑ\s]', '', texto)) < 2:
        return False
        
    return True

import re

def limpiar_nombre(nombre: str) -> str:
    """
    Limpia y formatea un nombre dado.

    Elimina prefijos comunes del nombre, como "me llamo", "soy", "mi nombre es", etc.
    Luego, capitaliza cada palabra del nombre y las une con espacios.

    Args:
        nombre (str): El nombre que se debe limpiar y formatear.

    Returns:
        str: El nombre limpio y formateado.
    """
    prefijos = [
        # Eliminar prefijos comunes del nombre
        r'^(?:me\s+llamo\s+)',
        r'^(?:soy\s+)',
        r'^(?:mi\s+nombre\s+es\s+)',
        r'^(?:ok\s+)',
        r'^(?:vale\s+vale\s+)',
        r'^(?:vale\s+)',
        r'^(?:hola\s+)',
        r'^(?:yo\s+)',
        r'^(?:pues\s+)',
    ]
    
    nombre = nombre.lower().strip()
    for prefijo in prefijos:
        nombre = re.sub(prefijo, '', nombre)
    
    return ' '.join(palabra.capitalize() for palabra in nombre.split())

import re

def detectar_rol(mensaje: str) -> str:
    """
    Detecta el rol del usuario basado en el mensaje proporcionado.

    El rol puede ser "jugador", "staff" o "técnico".
    Si no se detecta ningún rol, devuelve None.

    Args:
        mensaje (str): El mensaje a analizar.

    Returns:
        str: El rol detectado, o None si no se detecta ningún rol.
    """
    # Estas son algunas palabras comunes que se pueden usar para detectar el rol
    jugador = [
        r'j', r'jug', r'jugador', r'player', r'juego', r'tenista', r'1'
    ]
    staff = [
        r's', r'sta', r'staff', r'empleado', r'personal', r'trabajo', r'2'
    ]
    tecnico = [
        r't', r'tec', r'técnico', r'servicio', r'mantenimiento', r'3'
    ]

    # Convertir el mensaje a minúsculas para que la detección no distinga entre mayúsculas y minúsculas
    msg = mensaje.lower()

    # Verificar si alguna de las palabras del patrón de jugador está presente en el mensaje
    if any(re.search(patron, msg) for patron in jugador):
        return "jugador"

    # Verificar si alguna de las palabras del patrón de staff está presente en el mensaje
    if any(re.search(patron, msg) for patron in staff):
        return "staff"

    # Verificar si alguna de las palabras del patrón de técnico está presente en el mensaje
    if any(re.search(patron, msg) for patron in tecnico):
        return "técnico"

    # Si no se cumple ninguna de las condiciones anteriores, devolver None
    return None
