# ESP32 Voice Assistant Backend

Backend en Python (FastAPI) para el asistente de voz basado en ESP32.

Recibe audio (o texto), lo transcribe con **Groq Whisper**, detecta la intención
(reglas simples + respaldo con **Claude Haiku**) y devuelve el número de pista
que el DFPlayer Mini debe reproducir.

## Endpoints

- `GET /` → verifica que el servicio está vivo
- `POST /procesar-audio` → recibe un archivo de audio (`multipart/form-data`, campo `audio`)
- `POST /procesar-texto` → recibe `{"texto": "..."}` en JSON (útil si usas el
  SpeechRecognizer de App Inventor en el celular)

## Variables de entorno requeridas

| Variable | Descripción |
|---|---|
| `GROQ_API_KEY` | Clave de API de [Groq](https://console.groq.com) |
| `ANTHROPIC_API_KEY` | Clave de API de [Anthropic](https://console.anthropic.com) |

**Nunca subas estas claves al repositorio.** Se configuran directamente en Render.

## Despliegue en Render (paso a paso)

1. Sube estos archivos a tu repo de GitHub (ver sección siguiente).
2. En [Render](https://render.com) → **New +** → **Web Service**.
3. Conecta tu repo `ESP32-backend`.
4. Render debería detectar `render.yaml` automáticamente. Si no, configura a mano:
   - **Environment**: Python 3
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `uvicorn main:app --host 0.0.0.0 --port $PORT`
5. En la pestaña **Environment**, agrega `GROQ_API_KEY` y `ANTHROPIC_API_KEY`.
6. Despliega. Cuando termine, prueba abriendo la URL pública en el navegador:
   deberías ver `{"status": "ok", ...}`.
