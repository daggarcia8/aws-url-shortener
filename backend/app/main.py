
import os
import uuid
from datetime import datetime, timezone

import boto3
from botocore.exceptions import ClientError, BotoCoreError
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, HttpUrl

app = FastAPI(
    title="AWS URL Shortener",
    description="Acortador de enlaces con EC2 y DynamoDB",
    version="1.0.0"
)

AWS_REGION = os.getenv("AWS_REGION", "us-west-2")
TABLE_NAME = os.getenv("DYNAMODB_TABLE", "ShortUrls")

# Después configuraremos aquí el dominio de S3.
ALLOWED_ORIGINS = [
    origin.strip()
    for origin in os.getenv("ALLOWED_ORIGINS", "").split(",")
    if origin.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)

dynamodb = boto3.resource(
    "dynamodb",
    region_name=AWS_REGION
)

table = dynamodb.Table(TABLE_NAME)


class URLRequest(BaseModel):
    original_url: HttpUrl


@app.get("/")
def inicio():
    return {"mensaje": "Acortador AWS funcionando"}


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/shorten", status_code=201)
def shorten_url(data: URLRequest, request: Request):
    short_code = str(uuid.uuid4())
    original_url = str(data.original_url)
    created_at = datetime.now(timezone.utc).isoformat()

    item = {
        "short_code": short_code,
        "original_url": original_url,
        "created_at": created_at
    }

    try:
        table.put_item(
            Item=item,
            ConditionExpression="attribute_not_exists(short_code)"
        )
    except (ClientError, BotoCoreError):
        raise HTTPException(
            status_code=503,
            detail="No se pudo guardar el enlace"
        )

    base_url = str(request.base_url).rstrip("/")

    return {
        "short_code": short_code,
        "original_url": original_url,
        "short_url": f"{base_url}/{short_code}"
    }


def buscar_enlace(short_code: str):
    try:
        uuid.UUID(short_code)
    except ValueError:
        raise HTTPException(
            status_code=404,
            detail="Enlace no encontrado"
        )

    try:
        response = table.get_item(
            Key={"short_code": short_code}
        )
    except (ClientError, BotoCoreError):
        raise HTTPException(
            status_code=503,
            detail="Error al consultar DynamoDB"
        )

    item = response.get("Item")

    if not item:
        raise HTTPException(
            status_code=404,
            detail="Enlace no encontrado"
        )

    return item


@app.get("/urls/{short_code}")
def consultar_url(short_code: str):
    return buscar_enlace(short_code)


@app.get("/{short_code}")
def redireccionar(short_code: str):
    item = buscar_enlace(short_code)

    return RedirectResponse(
        url=item["original_url"],
        status_code=307
    )
