import os
import secrets
import base64
import logging
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
import edge_tts

# Configuration du logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Edge-TTS API (French Only)")
security = HTTPBasic()

WEB_USERNAME = os.getenv("WEB_USERNAME", "admin")
WEB_PASSWORD = os.getenv("WEB_PASSWORD", "password123")

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
        return f.read()

# Les fichiers statiques (JS, CSS) sont publics mais ils ne servent à rien sans l'accès à la page
app.mount("/static", StaticFiles(directory="static"), name="static")

# --- API Endpoints ---

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
async def list_voices():
    """Renvoie la liste des voix françaises disponibles."""
    return {"voices": VOICES}

class TTSRequest(BaseModel):
    text: str
    voice: str = "fr-FR-HenriNeural"
    # pitch, rate, volume pourraient être ajoutés plus tard

@app.post("/api/tts")
async def generate_tts(request: TTSRequest):
    """
    Génère la voix à la demande (on-demand) avec Edge-TTS.
    Le chargement et la génération sont très rapides et 100% CPU.
    """
    logger.info(f"Génération TTS demandée pour la voix: {request.voice}, texte: {request.text[:30]}...")
    try:
        communicate = edge_tts.Communicate(request.text, request.voice)
        audio_data = b""
        
        # Récupération de l'audio stream sans écrire sur le disque pour max de perfs
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                audio_data += chunk["data"]
        
        if not audio_data:
            raise Exception("L'audio généré est vide.")

        audio_base64 = base64.b64encode(audio_data).decode("utf-8")
        logger.info("Génération réussie.")
        return {"audio_base64": audio_base64}
    except Exception as e:
        logger.error(f"Erreur lors de la génération TTS: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health_check():
    return {"status": "ok"}
