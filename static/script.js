document.addEventListener('DOMContentLoaded', () => {
    const voiceSelect = document.getElementById('voiceSelect');
    const textInput = document.getElementById('textInput');
    const generateBtn = document.getElementById('generateBtn');
    const btnText = document.querySelector('.btn-text');
    const loader = document.querySelector('.loader');
    const resultContainer = document.getElementById('resultContainer');
    const audioPlayer = document.getElementById('audioPlayer');
    const downloadBtn = document.getElementById('downloadBtn');
    const downloadSrtBtn = document.getElementById('downloadSrtBtn');
    const errorContainer = document.getElementById('errorContainer');

    // Charger les voix au démarrage
    fetch('/api/voices', { headers: { 'X-API-Key': window.API_KEY } })
        .then(res => {
            if (!res.ok) throw new Error('Erreur API (Vérifiez la clé API)');
            return res.json();
        })
        .then(data => {
            voiceSelect.innerHTML = '';
            data.voices.forEach(voice => {
                const option = document.createElement('option');
                option.value = voice.id;
                option.textContent = `${voice.name} (${voice.gender})`;
                voiceSelect.appendChild(option);
            });
        })
        .catch(err => {
            showError("Impossible de charger les voix. Veuillez vérifier que le serveur est bien lancé.");
            console.error(err);
        });

    // Générer l'audio
    generateBtn.addEventListener('click', async () => {
        const text = textInput.value.trim();
        const voiceId = voiceSelect.value;

        if (!text) {
            showError("Veuillez entrer du texte.");
            return;
        }

        // UI Loading state
        hideError();
        resultContainer.classList.add('hidden');
        btnText.classList.add('hidden');
        loader.classList.remove('hidden');
        generateBtn.disabled = true;

        try {
            const response = await fetch('/api/tts', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-API-Key': window.API_KEY
                },
                body: JSON.stringify({
                    text: text,
                    voice: voiceId
                })
            });

            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.detail || `Erreur serveur: ${response.status}`);
            }

            const data = await response.json();
            
            // Créer le fichier audio depuis le Base64
            const audioSrc = `data:audio/mp3;base64,${data.audio_base64}`;
            audioPlayer.src = audioSrc;
            downloadBtn.href = audioSrc;
            
            // Fichier SRT
            const srtSrc = `data:text/plain;charset=utf-8;base64,${data.srt_base64}`;
            downloadSrtBtn.href = srtSrc;
            
            resultContainer.classList.remove('hidden');
            audioPlayer.play();

        } catch (error) {
            console.error(error);
            showError(error.message);
        } finally {
            // Restore UI state
            btnText.classList.remove('hidden');
            loader.classList.add('hidden');
            generateBtn.disabled = false;
        }
    });

    function showError(message) {
        errorContainer.textContent = message;
        errorContainer.classList.remove('hidden');
    }

    function hideError() {
        errorContainer.classList.add('hidden');
    }
});
