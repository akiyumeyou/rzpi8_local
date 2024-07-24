import os
import requests
import pygame
from google.cloud import texttospeech
import asyncio

# ElevenLabs APIキーの設定
ELEVENLABS_API_KEY = ''  # ここにAPIキーを入力

# Google Cloud Text-to-Speech API の初期化
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "rzpi_chat.json"
client = texttospeech.TextToSpeechClient()

async def google_text_to_speech(text, voice_params):
    print(f"Converting text to speech using Google Cloud TTS: {text}")  # デバッグ用ログ
    synthesis_input = texttospeech.SynthesisInput(text=text)

    audio_config = texttospeech.AudioConfig(
        audio_encoding=texttospeech.AudioEncoding.MP3
    )

    try:
        response = client.synthesize_speech(
            input=synthesis_input, voice=voice_params, audio_config=audio_config
        )
        print("Google Cloud TTS synthesis successful.")  # デバッグ用ログ
    except Exception as e:
        print(f"Google Cloud TTS synthesis failed: {e}")  # デバッグ用ログ
        return

    filename = "response.mp3"
    try:
        with open(filename, "wb") as out:
            out.write(response.audio_content)
        print(f"Audio content written to {filename}")  # デバッグ用ログ

        pygame.mixer.init()
        pygame.mixer.music.load(filename)
        pygame.mixer.music.play()
        print("Playing audio...")  # デバッグ用ログ

        while pygame.mixer.music.get_busy():
            await asyncio.sleep(0.1)

        print("Audio playback finished.")  # デバッグ用ログ
        os.remove(filename)
    except Exception as e:
        print(f"Error during audio playback: {e}")  # デバッグ用ログ

async def elevenlabs_text_to_speech(text, voice_id):
    print(f"Converting text to speech using ElevenLabs: {text}")  # デバッグ用ログ
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
    headers = {
        'Content-Type': 'application/json',
        'xi-api-key': ELEVENLABS_API_KEY
    }
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

    response = requests.post(url, headers=headers, json=data)
    response.raise_for_status()

    with open("response.mp3", "wb") as out:
        out.write(response.content)
    print(f"Generated speech for '{text}' and saved to response.mp3")

    pygame.mixer.init()
    pygame.mixer.music.load("response.mp3")
    pygame.mixer.music.play()
    print("Playing audio...")  # デバッグ用ログ

    while pygame.mixer.music.get_busy():
        await asyncio.sleep(0.1)

    os.remove("response.mp3")
    print("Audio playback finished.")  # デバッグ用ログ
