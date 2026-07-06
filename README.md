# Edge-TTS API

Une API RESTful rapide et légère basée sur [FastAPI](https://fastapi.tiangolo.com/) et [edge-tts](https://github.com/rany2/edge-tts) pour la génération de synthèse vocale (Text-To-Speech). Actuellement configurée pour fournir une sélection de voix francophones.

## Fonctionnalités

- **Génération TTS rapide** : Génération de voix à la demande sans nécessiter de GPU (100% CPU).
- **Voix Françaises** : Inclut une liste prédéfinie de voix francophones de haute qualité (France, Québec, Belgique, Suisse).
- **Sous-titres (Captions TikTok)** : Génère automatiquement des sous-titres au format SRT synchronisés au mot près (parfait pour les vidéos courtes).
- **Sécurité** :
  - **L'API** (les requêtes vers `/api/*`) est protégée par une clé passée dans le header HTTP `X-API-Key`.
  - **L'interface web** de test (`/`) est protégée par une authentification HTTP basique pour empêcher l'abus public.
- **Réponse Base64** : L'API renvoie l'audio généré et les sous-titres encodés en base64 pour une intégration facile sans stockage temporaire sur disque.
- **Dockerisé** : Prêt à être déployé facilement avec Docker et Docker Compose.

## Prérequis

- Python 3.11+
- FFmpeg (si vous l'exécutez localement sans Docker)
- Docker et Docker Compose (recommandé)

## Installation et Lancement

### Avec Docker Compose (Recommandé)

1. Clonez ce dépôt.
2. Définissez les identifiants de l'interface web et la clé d'API dans un fichier `.env` à la racine :
   ```env
   WEB_USERNAME=admin
   WEB_PASSWORD=password123
   API_KEY=change_me_in_docker_compose
   ```
3. Démarrez l'application :
   ```bash
   docker-compose up -d --build
   ```
L'API sera accessible sur `http://localhost:8006`. L'interface web est disponible à la racine (`/`).

### En local (sans Docker)

1. Assurez-vous d'avoir FFmpeg installé sur votre système.
2. Créez un environnement virtuel et activez-le :
   ```bash
   python -m venv venv
   # Sur Windows :
   venv\Scripts\activate
   # Sur Linux/Mac :
   source venv/bin/activate
   ```
3. Installez les dépendances :
   ```bash
   pip install -r requirements.txt
   ```
4. Définissez les variables d'environnement (optionnel, valeurs par défaut si non spécifiées) :
   ```bash
   set WEB_USERNAME=admin
   set WEB_PASSWORD=monmotdepasse
   set API_KEY=votre_cle_api_secrete
   ```
5. Démarrez le serveur Uvicorn :
   ```bash
   uvicorn main:app --host 0.0.0.0 --port 8000
   ```
L'API sera accessible sur `http://localhost:8000`.

## Endpoints de l'API

### `GET /`
Affiche l'interface web (protégée par Basic Auth avec les variables d'environnement `WEB_USERNAME` et `WEB_PASSWORD`).

### `GET /api/voices`
Retourne la liste des voix françaises disponibles au format JSON.
**En-tête requis** : `X-API-Key: votre_cle_api`

### `POST /api/tts`
Génère l'audio et les sous-titres (SRT) à partir du texte fourni.
**En-tête requis** : `X-API-Key: votre_cle_api`

**Payload JSON attendu :**
```json
{
  "text": "Bonjour, comment allez-vous ?",
  "voice": "fr-FR-HenriNeural",
  "words_per_sub": 2
}
```
*(Le paramètre `words_per_sub` est optionnel et permet de définir le nombre de mots par sous-titre pour le style TikTok. Par défaut : 2)*

**Réponse :**
```json
{
  "audio_base64": "UklGR... (chaîne base64 de l'audio)",
  "srt_base64": "MQ0KMDA... (chaîne base64 du fichier SRT)"
}
```

### `GET /health`
Endpoint pour vérifier l'état de santé de l'API (utile pour Docker). Retourne `{"status": "ok"}`.

## Stack Technique

- **Python** avec [FastAPI](https://fastapi.tiangolo.com/)
- [edge-tts](https://github.com/rany2/edge-tts) pour la communication avec le service de Microsoft Edge
- Serveur ASGI [Uvicorn](https://www.uvicorn.org/)
