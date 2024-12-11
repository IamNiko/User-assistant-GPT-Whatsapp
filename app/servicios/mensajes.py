def dividir_mensaje(mensaje: str, limite: int = 1500) -> list:
    """
    Divide un mensaje largo en partes más pequeñas mientras respeta palabras completas.
    Está optimizado para manejar palabras largas y asegurar un buen rendimiento.

    Args:
        mensaje (str): El mensaje que se va a dividir.
        limite (int): La longitud máxima de cada parte dividida. Por defecto es 1500.

    Returns:
        list: Una lista de cadenas donde cada cadena es una parte del mensaje original
              que no excede el límite especificado.
    """
    # Retorna el mensaje como una sola parte si está dentro del límite
    if len(mensaje) <= limite:
        return [mensaje]

    palabras = mensaje.split()  # Divide el mensaje en palabras
    partes = []  # Lista para almacenar las partes del mensaje
    parte_actual = []  # Parte actual que se está construyendo

    for palabra in palabras:
        # Si una sola palabra excede el límite, dividir la palabra en sí misma
        if len(palabra) > limite:
            if parte_actual:
                # Agregar la parte actual a partes si no está vacía
                partes.append(" ".join(parte_actual))
                parte_actual = []
            # Divide la palabra larga en fragmentos del límite especificado
            partes.extend([palabra[i:i+limite] for i in range(0, len(palabra), limite)])
        elif sum(len(w) + 1 for w in parte_actual) + len(palabra) <= limite:
            # Agregar palabra a la parte actual si cabe dentro del límite
            parte_actual.append(palabra)
        else:
            # De lo contrario, finalizar la parte actual y comenzar una nueva
            partes.append(" ".join(parte_actual))
            parte_actual = [palabra]

    # Agrega cualquier palabra restante en la parte actual
    if parte_actual:
        partes.append(" ".join(parte_actual))

    return partes

def es_agradecimiento(mensaje: str) -> bool:
    agradecimientos = [
        "ok gracias", "gracias", "ok", "vale", "perfecto", "genial", 
        "muchas gracias", "thank", "thanks", "ok thank", "graciass"
    ]
    return any(agradecimiento in mensaje.lower() for agradecimiento in agradecimientos)
