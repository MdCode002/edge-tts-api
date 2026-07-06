import os
import secrets
import base64
import logging
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from fastapi.security import APIKeyHeader
from pydantic import BaseModel
import edge_tts

# Configuration du logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Edge-TTS API (French Only)")
security = HTTPBasic()

WEB_USERNAME = os.getenv("WEB_USERNAME", "admin")
WEB_PASSWORD = os.getenv("WEB_PASSWORD", "password123")
API_KEY = os.getenv("API_KEY", "change_me_in_docker_compose")

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

def get_api_key(api_key: str = Depends(api_key_header)):
    if API_KEY and api_key != API_KEY:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Invalid or missing API Key."
        )
    return api_key

def verify_credentials(credentials: HTTPBasicCredentials = Depends(security)):
    correct_username = secrets.compare_digest(credentials.username, WEB_USERNAME)
    correct_password = secrets.compare_digest(credentials.password, WEB_PASSWORD)
    if not (correct_username and correct_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Identifiants incorrects",
            headers={"WWW-Authenticate": "Basic"},
        )
    return credentials.username

# Servir l'interface web (Protégée par mot de passe)
@app.get("/", response_class=HTMLResponse)
async def get_ui(username: str = Depends(verify_credentials)):
    with open("static/index.html", "r", encoding="utf-8") as f:
        content = f.read()
        # Inject API_KEY so the frontend JS can use it
        return content.replace("{{API_KEY}}", API_KEY)

# Les fichiers statiques (JS, CSS) sont publics mais ils ne servent à rien sans l'accès à la page
app.mount("/static", StaticFiles(directory="static"), name="static")

# --- API Endpoints ---

def ms_to_srt_time(ms: int) -> str:
    seconds, milliseconds = divmod(int(ms), 1000)
    minutes, seconds = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d},{milliseconds:03d}"

def words_to_srt(words: list[dict], words_per_sub: int = 2) -> str:
    srt_lines: list[str] = []
    idx = 1
    i = 0
    while i < len(words):
        group = words[i : i + words_per_sub]
        start_ms = group[0]["startMs"]
        end_ms = group[-1]["endMs"]
        if end_ms <= start_ms:
            end_ms = start_ms + 100
        srt_lines.append(str(idx))
        srt_lines.append(f"{ms_to_srt_time(start_ms)} --> {ms_to_srt_time(end_ms)}")
        srt_lines.append(" ".join(w["text"] for w in group))
        srt_lines.append("")
        idx += 1
        i += words_per_sub
    return "\n".join(srt_lines)

VOICES = [
    {"id": "fr-FR-RemyMultilingualNeural", "name": "Rémy (Multilingual, Expressif)", "gender": "Male"},
    {"id": "fr-FR-VivienneMultilingualNeural", "name": "Vivienne (Multilingual, Expressive)", "gender": "Female"},
    {"id": "fr-FR-HenriNeural", "name": "Henri", "gender": "Male"},
    {"id": "fr-FR-DeniseNeural", "name": "Denise", "gender": "Female"},
    {"id": "fr-FR-ClaudeNeural", "name": "Claude", "gender": "Male"},
    {"id": "fr-FR-CoralieNeural", "name": "Coralie", "gender": "Female"},
    {"id": "fr-FR-AlainNeural", "name": "Alain", "gender": "Male"},
    {"id": "fr-FR-BrigitteNeural", "name": "Brigitte", "gender": "Female"},
    {"id": "fr-FR-CelesteNeural", "name": "Céleste", "gender": "Female"},
    {"id": "fr-FR-EloiseNeural", "name": "Éloïse", "gender": "Female"},
    {"id": "fr-FR-JacquelineNeural", "name": "Jacqueline", "gender": "Female"},
    {"id": "fr-FR-JeromeNeural", "name": "Jérôme", "gender": "Male"},
    {"id": "fr-FR-JosephineNeural", "name": "Joséphine", "gender": "Female"},
    {"id": "fr-FR-MauriceNeural", "name": "Maurice", "gender": "Male"},
    {"id": "fr-FR-YvesNeural", "name": "Yves", "gender": "Male"},
    {"id": "fr-FR-YvetteNeural", "name": "Yvette", "gender": "Female"},
    {"id": "fr-CA-AntoineNeural", "name": "Antoine (Québec)", "gender": "Male"},
    {"id": "fr-CA-SylvieNeural", "name": "Sylvie (Québec)", "gender": "Female"},
    {"id": "fr-BE-GerardNeural", "name": "Gérard (Belgique)", "gender": "Male"},
    {"id": "fr-BE-CharlineNeural", "name": "Charline (Belgique)", "gender": "Female"},
    {"id": "fr-CH-ThierryNeural", "name": "Thierry (Suisse)", "gender": "Male"},
    {"id": "fr-CH-ArianeNeural", "name": "Ariane (Suisse)", "gender": "Female"}
]

@app.get("/api/voices")
async def list_voices(api_key: str = Depends(get_api_key)):
    """Renvoie la liste des voix françaises disponibles."""
    return {"voices": VOICES}

class TTSRequest(BaseModel):
    text: str
    voice: str = "fr-FR-HenriNeural"
    words_per_sub: int = 2
    # pitch, rate, volume pourraient être ajoutés plus tard

@app.post("/api/tts")
async def generate_tts(request: TTSRequest, api_key: str = Depends(get_api_key)):
    """
    Génère la voix à la demande (on-demand) avec Edge-TTS.
    Le chargement et la génération sont très rapides et 100% CPU.
    """
    logger.info(f"Génération TTS demandée pour la voix: {request.voice}, texte: {request.text[:30]}...")
    try:
        communicate = edge_tts.Communicate(request.text, request.voice)
        audio_data = b""
        all_words = []
        
        # Récupération de l'audio stream sans écrire sur le disque pour max de perfs
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                audio_data += chunk["data"]
            elif chunk["type"] == "WordBoundary":
                # offset et duration sont en 100-nanosecondes. / 10000 pour avoir des ms.
                start_ms = chunk["offset"] / 10000
                end_ms = (chunk["offset"] + chunk["duration"]) / 10000
                all_words.append({
                    "text": chunk["text"],
                    "startMs": int(start_ms),
                    "endMs": int(end_ms),
                })
        
        if not audio_data:
            raise Exception("L'audio généré est vide.")

        audio_base64 = base64.b64encode(audio_data).decode("utf-8")
        srt_content = words_to_srt(all_words, request.words_per_sub)
        srt_base64 = base64.b64encode(srt_content.encode("utf-8")).decode("utf-8")

        logger.info("Génération réussie.")
        return {
            "audio_base64": audio_base64,
            "srt_base64": srt_base64
        }
    except Exception as e:
        logger.error(f"Erreur lors de la génération TTS: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health_check():
    return {"status": "ok"}
