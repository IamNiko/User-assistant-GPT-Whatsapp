from decouple import config

TECH_ACCESS_KEY = config("TECH_ACCESS_KEY")
print(f"Clave técnica cargada desde .env: {TECH_ACCESS_KEY}")

