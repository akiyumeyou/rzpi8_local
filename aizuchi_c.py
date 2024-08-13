import os
import requests

# ElevenLabs APIキーの設定
ELEVENLABS_API_KEY = 'sk_83a724eba4e327d3aa828920bf57839a5b0cc3f93f5c9718'  # ここにAPIキーを入力
VOICE_ID = 'FeaM2xaHKiX1yiaPxvwe'  # ここに女性の声のIDを入力

phrases = [
    "haee",
    "hoo" 
]

def generate_speech(phrase, filename):
    try:
        print(f"Generating speech for phrase: {phrase}")

        url = f"https://api.elevenlabs.io/v1/text-to-speech/{VOICE_ID}"
        headers = {
            'Content-Type': 'application/json',
            'xi-api-key': ELEVENLABS_API_KEY
        }
        data = {
            "text": phrase,
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
        print(f"API response: {response}")

        if not response.content:
            print(f"No audio content returned for phrase '{phrase}'")
            return

        with open(filename, "wb") as out:
            out.write(response.content)
        print(f"Generated speech for '{phrase}' and saved to {filename}")

    except Exception as e:
        print(f"An error occurred: {e}")

for phrase in phrases:
    filename = f"{phrase}_c.mp3"  # ファイル名に「_c」を追加
    generate_speech(phrase, filename)
