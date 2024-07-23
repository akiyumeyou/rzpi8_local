import os
from google.cloud import texttospeech

# Google Cloud Text-to-Speech API の初期化
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "rzpi_chat.json"  # ここにあなたのサービスアカウントファイルのパスを入力してください
client = texttospeech.TextToSpeechClient()

phrases = [
    "そうなんですね",
    "なるほど",
    "へーそうなんですね",
    "ほーそれは興味深いですね",
    "そうですね",
    "それは大変ですね",
    "うんうん、わたしも好きです",
    "それは残念です",
    "それは楽しいですね",
    "それは嬉しいですね",
    "それは悲しいですね",
    "それはつらいですね",
    "それで"
]

def generate_speech(phrase, filename):
    try:
        print(f"Generating speech for phrase: {phrase}")
        synthesis_input = texttospeech.SynthesisInput(text=phrase)

        voice = texttospeech.VoiceSelectionParams(
            language_code="ja-JP",
            name="ja-JP-Standard-C",  # 男性の声
            ssml_gender=texttospeech.SsmlVoiceGender.MALE
        )

        audio_config = texttospeech.AudioConfig(
            audio_encoding=texttospeech.AudioEncoding.MP3
        )

        response = client.synthesize_speech(
            input=synthesis_input, voice=voice, audio_config=audio_config
        )

        print(f"API response: {response}")

        if not response.audio_content:
            print(f"No audio content returned for phrase '{phrase}'")
            return

        with open(filename, "wb") as out:
            out.write(response.audio_content)
        print(f"Generated speech for '{phrase}' and saved to {filename}")

    except Exception as e:
        print(f"An error occurred: {e}")

for phrase in phrases:
    filename = f"{phrase}.mp3"
    generate_speech(phrase, filename)
