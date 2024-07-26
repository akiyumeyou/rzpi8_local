import os
import io
import requests
from google.cloud import texttospeech
from pydub import AudioSegment
from pydub.playback import play

# Google Cloud Text-to-Speech API の初期化
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "/Users/satouakiko/Desktop/PY/rzpi_chat.json"
client = texttospeech.TextToSpeechClient()

# ElevenLabsのAPIキーを直接指定
ELEVENLABS_API_KEY = ''

async def google_text_to_speech(text, voice_params):
    synthesis_input = texttospeech.SynthesisInput(text=text)
    audio_config = texttospeech.AudioConfig(audio_encoding=texttospeech.AudioEncoding.MP3)
    try:
        response = client.synthesize_speech(input=synthesis_input, voice=voice_params, audio_config=audio_config)
        print("Google Cloud TTS synthesis successful.")
        return response.audio_content
    except Exception as e:
        print(f"Google Cloud TTS synthesis failed: {e}")
        return None

async def elevenlabs_text_to_speech(text, voice_id):
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
    headers = {'Content-Type': 'application/json', 'xi-api-key': ELEVENLABS_API_KEY}
    data = {
        "text": text,
        "model_id": "eleven_multilingual_v2",
        "voice_settings": {
            "stability": 0.5,
            "similarity_boost": 1.0,
            "style": 0.2,
            "use_speaker_boost": True,
            "speed": 1.0,
            "pitch": 1.0
        }
    }
    try:
        response = requests.post(url, headers=headers, json=data)
        response.raise_for_status()
        print("ElevenLabs TTS synthesis successful.")
        return response.content
    except Exception as e:
        print(f"ElevenLabs TTS synthesis failed: {e}")
        return None

async def play_audio(audio_content):
    try:
        audio = AudioSegment.from_file(io.BytesIO(audio_content), format="mp3")
        play(audio)
    except Exception as e:
        print(f"Error playing audio: {e}")
