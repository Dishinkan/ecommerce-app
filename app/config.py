# app/config.py

import os

# Base directory del progetto
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Cartella statica (CSS, JS, immagini)
STATIC_DIR = os.path.join(BASE_DIR, "static")

# Cartella upload immagini
UPLOADS_DIR = os.path.join(STATIC_DIR, "uploads")

# Crea le cartelle se non esistono
os.makedirs(STATIC_DIR, exist_ok=True)
os.makedirs(UPLOADS_DIR, exist_ok=True)
