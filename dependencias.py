import sys
import subprocess

paquetes = [
    "numpy",
    "scipy",
    "pandas",
    "matplotlib",
    "fitter",
]

subprocess.check_call([sys.executable, "-m", "pip", "install", *paquetes])

#! EJECUTAR UNA SOLA VEZ ANTES DE CUALQUIER SCRIPT CON EL COMANDO: python dependencias.py