# src/main.py
from fastapi import FastAPI

# Inicializamos la aplicación
app = FastAPI(
    title="UTBOOKLM",
    description="API REST para el sistema SaaS",
    version="1.0.0"
)

# Nuestro primer endpoint de prueba
@app.get("/")
def read_root():
    return {"status": "ok", "message": "Probando"}