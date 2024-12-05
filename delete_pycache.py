import os
import shutil

for root, dirs, files in os.walk(".", topdown=False):
    for name in dirs:
        if name == "__pycache__":
            dir_path = os.path.join(root, name)
            print(f"Eliminando: {dir_path}")
            shutil.rmtree(dir_path)
