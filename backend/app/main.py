
from fastapi import FastAPI

app = FastAPI(
    title="AWS URL Shortener",
    description="API para acortar enlaces utilizando AWS",
    version="1.0.0"
)

@app.get("/")
def inicio():
    return {
        "mensaje": "Bienvenido al acortador de enlaces AWS",
        "estado": "funcionando"
    }

@app.get("/health")
def verificar_estado():
    return {
        "status": "ok",
        "servicio": "FastAPI"
    }
