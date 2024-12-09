proyecto_pkap/
├── app/
│   ├── __init__.py
│   ├── main.py           # Punto de entrada de la aplicación FastAPI
│   ├── configuracion.py  # Configuraciones del sistema
│   ├── nucleo/
│   │   ├── __init__.py
│   │   ├── estados.py    # Gestión de estados de usuario
│   │   └── validadores.py # Validación de nombres y otros
│   ├── base_datos/
│   │   ├── __init__.py
│   │   ├── modelos.py    # Modelos SQLAlchemy
│   │   └── sesion.py     # Gestión de sesión de base de datos
│   ├── servicios/
│   │   ├── __init__.py
│   │   ├── gpt.py        # Integración con GPT-4
│   │   ├── twilio.py     # Servicio de mensajería Twilio
│   │   └── mensajes.py   # Manejo y división de mensajes
│   ├── rutas/
│   │   ├── __init__.py
│   │   └── webhook.py    # Manejadores de rutas webhook
│   └── utilidades/
│       ├── __init__.py
│       └── ayudantes.py  # Funciones auxiliares
├── prompts/
│   └── prompt_base.txt   # Prompts del sistema
├── pruebas/
│   ├── __init__.py
│   ├── test_validadores.py
│   └── test_servicios.py
├── .env                  # Variables de entorno
├── requirements.txt      # Dependencias del proyecto
└── README.md            # Documentación del proyecto





El proyecto sigue una estructura modular para facilitar el mantenimiento y la escalabilidad:

- `app/`: Código principal de la aplicación
- `app/nucleo/`: Componentes centrales
- `app/servicios/`: Servicios externos (GPT-4, Twilio)
- `app/base_datos/`: Modelos y gestión de base de datos