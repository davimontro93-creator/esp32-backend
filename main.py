"""
Backend para el asistente de voz ESP32
----------------------------------------
Flujo:
1. El ESP32 (o la app de App Inventor) envía un audio grabado al endpoint /procesar-audio
2. Groq Whisper transcribe el audio a texto en español
3. Se busca la intención primero con reglas simples (rápido y gratis)
4. Si no hay coincidencia clara, se usa Claude Haiku como respaldo para interpretar la intención
5. Se devuelve un JSON con el número de pista (track) que el DFPlayer debe reproducir

Variables de entorno necesarias (configurarlas en Render, NO en el código):
  GROQ_API_KEY       -> clave de Groq (para Whisper)
  ANTHROPIC_API_KEY  -> clave de Anthropic (para Claude Haiku, respaldo)
"""

import os
import json
import tempfile
from datetime import datetime
from zoneinfo import ZoneInfo

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from groq import Groq
from anthropic import Anthropic

app = FastAPI(title="ESP32 Voice Assistant Backend")

# Permitir llamadas desde cualquier origen (el ESP32 y la app no envían origen de navegador,
# pero si luego pruebas desde un navegador o Postman esto evita bloqueos de CORS)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Los clientes se crean una sola vez y leen la clave desde las variables de entorno
groq_client = Groq(api_key=os.environ.get("GROQ_API_KEY"))
anthropic_client = Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))

# ---------------------------------------------------------------------------
# MAPA DE INTENCIONES -> NÚMERO DE PISTA EN LA MICRO SD (DFPlayer)
# Ajusta estos números para que coincidan con el orden real de tus archivos
# en la tarjeta SD (normalmente 0001.mp3, 0002.mp3, etc.)
# ---------------------------------------------------------------------------
TRACK_MAP = {
    "saludo": 1,
    "hora": 2,
    "clima": 3,
    "chiste": 4,
    "encender_luz": 5,
    "apagar_luz": 6,
    "despedida": 7,
    "desconocido": 8,  # pista de "no entendí, ¿puedes repetir?"
}

# Palabras clave simples por intención (más rápido y sin costo que llamar a Claude)
REGLAS = {
    "saludo": ["hola", "buenos días", "buenas tardes", "buenas noches"],
    "hora": ["hora", "qué hora es"],
    "clima": ["clima", "temperatura", "va a llover"],
    "chiste": ["chiste", "cuéntame algo gracioso"],
    "encender_luz": ["enciende la luz", "prende la luz", "enciende el led"],
    "apagar_luz": ["apaga la luz", "apaga el led"],
    "despedida": ["adiós", "hasta luego", "chao"],
}


def detectar_intencion_por_reglas(texto: str) -> str | None:
    """Intenta encontrar la intención usando coincidencia simple de palabras clave."""
    texto_normalizado = texto.lower().strip()
    for intencion, palabras in REGLAS.items():
        for palabra in palabras:
            if palabra in texto_normalizado:
                return intencion
    return None


def detectar_intencion_con_claude(texto: str) -> str:
    """
    Respaldo con Claude Haiku: si las reglas simples no detectaron nada,
    le pedimos a Claude que elija la intención más parecida de la lista.
    """
    intenciones_disponibles = list(TRACK_MAP.keys())

    prompt = (
        "Eres un clasificador de intenciones para un asistente de voz en español. "
        f"El usuario dijo: \"{texto}\". "
        f"Elige EXACTAMENTE una de estas intenciones (responde solo la palabra, nada más): "
        f"{', '.join(intenciones_disponibles)}."
    )

    respuesta = anthropic_client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=20,
        messages=[{"role": "user", "content": prompt}],
    )

    intencion = respuesta.content[0].text.strip().lower()

    # Verificación de seguridad: si Claude devuelve algo fuera de la lista, usamos "desconocido"
    if intencion not in TRACK_MAP:
        intencion = "desconocido"

    return intencion


def generar_respuesta_ia(texto: str) -> str:
    """
    Genera una respuesta conversacional corta con Claude, para mostrarla
    en el Serial Monitor del ESP32. Esto es independiente de la clasificación
    de intención (que se sigue usando para elegir la pista del DFPlayer):
    aquí simplemente le contestamos al usuario en lenguaje natural.
    """
    ahora = datetime.now(ZoneInfo("America/Costa_Rica"))
    hora_actual = ahora.strftime("%I:%M %p del %d/%m/%Y")

    prompt = (
        "Eres un asistente de voz amigable que responde en español. "
        "Responde de forma breve (máximo 2 frases cortas) y natural, "
        "como si hablaras en voz alta. "
        f"La hora y fecha actual es: {hora_actual} (hora de Costa Rica). "
        "Si el usuario pregunta la hora o la fecha, usa este dato exacto. "
        f"El usuario dijo: \"{texto}\"."
    )

    try:
        respuesta = anthropic_client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=100,
            messages=[{"role": "user", "content": prompt}],
        )
        return respuesta.content[0].text.strip()
    except Exception:
        # Si falla, no tumbamos el endpoint: simplemente no habrá texto de respuesta
        return ""


@app.get("/")
def raiz():
    """Endpoint simple para confirmar que el servicio está activo (útil para revisar en Render)."""
    return {"status": "ok", "mensaje": "Backend del asistente de voz ESP32 activo"}


@app.post("/procesar-audio")
async def procesar_audio(audio: UploadFile = File(...)):
    """
    Recibe un archivo de audio, lo transcribe y devuelve la intención + número de pista.

    Respuesta de ejemplo:
    {
      "texto": "hola cómo estás",
      "intencion": "saludo",
      "track": 1,
      "respuesta": "¡Hola! Estoy muy bien, ¿en qué te ayudo hoy?"
    }
    """
    # Guardar el audio temporalmente porque Groq necesita un archivo, no bytes crudos
    sufijo = os.path.splitext(audio.filename or "audio.wav")[1] or ".wav"
    with tempfile.NamedTemporaryFile(delete=False, suffix=sufijo) as archivo_temp:
        contenido = await audio.read()
        archivo_temp.write(contenido)
        ruta_temp = archivo_temp.name

    try:
        with open(ruta_temp, "rb") as f:
            transcripcion = groq_client.audio.transcriptions.create(
                file=f,
                model="whisper-large-v3",
                language="es",
            )
        texto = transcripcion.text
    except Exception as error:
        raise HTTPException(status_code=500, detail=f"Error al transcribir audio: {error}")
    finally:
        os.remove(ruta_temp)

    # 1) Intentar con reglas simples
    intencion = detectar_intencion_por_reglas(texto)

    # 2) Si no hubo coincidencia, usar Claude como respaldo
    if intencion is None:
        try:
            intencion = detectar_intencion_con_claude(texto)
        except Exception as error:
            # Si falla Claude, no tumbamos el servicio: devolvemos "desconocido"
            intencion = "desconocido"

    track = TRACK_MAP.get(intencion, TRACK_MAP["desconocido"])
    respuesta_ia = generar_respuesta_ia(texto)

    return {
        "texto": texto,
        "intencion": intencion,
        "track": track,
        "respuesta": respuesta_ia,
    }


@app.post("/procesar-texto")
async def procesar_texto(payload: dict):
    """
    Endpoint alterno para cuando el texto ya viene listo desde la app
    (por ejemplo, si usas el SpeechRecognizer de App Inventor en el celular
    en vez de enviar audio crudo desde el ESP32).

    Cuerpo esperado: {"texto": "enciende la luz"}
    """
    texto = payload.get("texto", "")
    if not texto:
        raise HTTPException(status_code=400, detail="Falta el campo 'texto'")

    intencion = detectar_intencion_por_reglas(texto)
    if intencion is None:
        try:
            intencion = detectar_intencion_con_claude(texto)
        except Exception:
            intencion = "desconocido"

    track = TRACK_MAP.get(intencion, TRACK_MAP["desconocido"])

    return {
        "texto": texto,
        "intencion": intencion,
        "track": track,
    }
