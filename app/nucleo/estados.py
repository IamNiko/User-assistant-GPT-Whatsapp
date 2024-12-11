from typing import Dict, Any# Gestión de estados de usuariofrom typing import Dict, Any

class GestorEstados:
    """
    Clase que se encarga de gestionar los estados de los usuarios.

    El estado de un usuario es un diccionario que contiene los siguientes campos:
    - "paso": El paso actual en el flujo de conversacion.
    - "nombre": El nombre del usuario.
    - "rol": El rol del usuario.
    - "ha_pagado": Un booleano que indica si el usuario ha pagado.

    La clase utiliza un diccionario para almacenar los estados de todos los usuarios.
    La clave del diccionario es el n mero de tel fono del usuario y el valor es el
    estado actual del usuario.
    """
    def __init__(self):
        """
        Constructor de la clase.

        Inicializa el diccionario que se utiliza para almacenar los estados de los
        usuarios.
        """
        self.estados_usuario: Dict[str, Dict[str, Any]] = {}


    def obtener_estado_inicial(self, remitente: str) -> Dict[str, Any]:
        """
        Crea un estado inicial para el usuario.

        El estado inicial contiene los siguientes campos:
        - "paso": El paso actual en el flujo de conversaci n.
        - "nombre": El nombre del usuario.
        - "rol": El rol del usuario.
        - "ha_pagado": Un booleano que indica si el usuario ha pagado.
        - "acceso_tecnico": Un booleano que indica si el usuario tiene acceso t cnico.
        - "remitente": El n mero de tel fono del usuario.
        - "historial_conversacion": Un lista vac a para almacenar el historial de la conversacion.
        """
        return {
            "paso": "inicio",
            "nombre": None,
            "rol": None,
            "acceso_tecnico": False,
            "remitente": remitente,
            "historial_conversacion": []
        }

    def obtener_estado(self, remitente: str) -> Dict[str, Any]:
        """
        Obtiene el estado actual del usuario.

        Si el usuario no tiene un estado previo, se crea uno nuevo con el estado inicial.
        """
        if remitente not in self.estados_usuario:
            # Si el usuario no tiene un estado previo, se crea uno nuevo
            # con el estado inicial
            self.estados_usuario[remitente] = self.obtener_estado_inicial(remitente)
        return self.estados_usuario[remitente]

    def actualizar_estado(self, remitente: str, estado: Dict[str, Any]) -> None:

        self.estados_usuario[remitente] = estado

    def reanudar_estado(self, remitente: str) -> str:
        estado = self.obtener_estado(remitente)
        if estado["paso"] == "inicio":
            return "¡Hola de nuevo! ¿Cómo puedo ayudarte?"
        # Continuar en el paso guardado
        return f"Continuemos desde donde lo dejamos, {estado['paso']}."
    
    def guardar_estado_en_bd(self, remitente: str, estado: Dict[str, Any]):
    # Aquí implementa la lógica para guardar en tu base de datos
        pass

    
gestor_estados = GestorEstados()