from pathlib import Path
from typing import Dict

class GestorPrompts:
    def __init__(self):
        self.prompts: Dict[str, str] = {}
        self.cargar_prompts()
    
    def cargar_prompts(self) -> None:
        """Carga todos los prompts desde los archivos

        El método intenta abrir y leer los archivos de prompts en el directorio
        GPT_BOT/prompts/, y almacena el contenido en un diccionario. Si no se
        encuentra un archivo, se registra un mensaje de advertencia y se agrega
        un texto de reemplazo en el diccionario.
        """
        prompt_files = {
            'base': 'Prompt_base',
            'jugador': 'Prompt_player',
            'tecnico': 'Prompt_tech',
            'staff': 'Prompt_staff'
        }
        
        # Obtener la ruta del directorio actual del script
        current_file = Path(__file__).resolve()
        
        # Navegar al directorio GPT_BOT/prompts/
        prompts_dir = current_file.parent.parent.parent / 'prompts'
        
        print(f"Buscando prompts en: {prompts_dir}")  # Para debugging
        
        for key, filename in prompt_files.items():
            file_path = prompts_dir / filename
            try:
                print(f"Intentando abrir: {file_path}")  # Para debugging
                if file_path.exists():
                    with open(file_path, 'r', encoding='utf-8') as file:
                        self.prompts[key] = file.read()
                else:
                    print(f"El archivo no existe: {file_path}")
                    raise FileNotFoundError
            except FileNotFoundError:
                print(f"Advertencia: No se encontró {filename}")
                # Agregar un texto de reemplazo
                self.prompts[key] = f"No se pudo cargar el prompt de {key}"
            except Exception as e:
                print(f"Error al leer {filename}: {str(e)}")
                # Agregar un texto de reemplazo
                self.prompts[key] = f"Error al cargar el prompt de {key}"
    
    def obtener_prompt(self, tipo: str) -> str:
        """
        Obtiene el prompt correspondiente al tipo de usuario especificado.

        Args:
            tipo (str): El tipo de usuario para el cual se desea obtener el prompt
                        (puede ser 'jugador', 'staff', 'tecnico', etc.).

        Returns:
            str: El prompt asociado con el tipo de usuario. Si el tipo no es
                 reconocido, devuelve el prompt base por defecto.
        """
        # Intentar obtener el prompt para el tipo especificado
        return self.prompts.get(tipo, self.prompts['base'])

gestor_prompts = GestorPrompts()