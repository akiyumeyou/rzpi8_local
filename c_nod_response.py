import os
import random
import pygame
import asyncio
from c_text_to_speech import google_text_to_speech, elevenlabs_text_to_speech

# 共感応答のルール設定
response_rules = {
    "endings": {
        "です。": "そうなんですね。",
        "思います": "そうなんですね。",
        "ました。": "へえ、そうなんですね。",
        "だったんですよ。": "ほー、それは興味深いですね。",
        "ます。": "そうですね。"
    },
    "keywords": {
        "困っています": "それは大変ですね。",
        "好きです": "うんうん、私も好きです。",
        "嫌い": "それは残念ですね。",
        "楽しい": "それは楽しいですね。",
        "嬉しい": "それは嬉しいですね。",
        "悲しい": "それは悲しいですね。",
        "辛い": "それは辛いですね。"
    }
}

# 事前録音した相槌の音声ファイル
nod_responses_default = ["hoo.mp3", "naruhodo.mp3", "hee.mp3"]
nod_responses_custom = ["hoo_c.mp3", "naruhodo_c.mp3", "hee_c.mp3"]

async def play_nod_response(custom_voice=False):
    nod_responses = nod_responses_custom if custom_voice else nod_responses_default
    nod_file = random.choice(nod_responses)

    print(f"Playing nod response: {nod_file}")  # デバッグ用ログ
    if not os.path.exists(nod_file):
        print(f"File not found: {nod_file}")  # エラーログ
        return

    pygame.mixer.init()
    pygame.mixer.music.load(nod_file)
    pygame.mixer.music.play()

    while pygame.mixer.music.get_busy():
        await asyncio.sleep(0.1)

async def generate_custom_response(speech, custom_voice=False):
    for keyword, response in response_rules["keywords"].items():
        if keyword in speech:
            await play_response(response, custom_voice)
            return response

    for ending, response in response_rules["endings"].items():
        if speech.endswith(ending):
            await play_response(response, custom_voice)
            return response

    # デフォルトの相槌
    default_response = random.choice(["へー", "ほー", "そうですね"])
    await play_response(default_response, custom_voice)
    return default_response

async def play_response(response, custom_voice):
    if custom_voice:
        await elevenlabs_text_to_speech(response, "FeaM2xaHKiX1yiaPxvwe")
    else:
        await google_text_to_speech(response, texttospeech.VoiceSelectionParams(
            language_code="ja-JP",
            name="ja-JP-Standard-C",
            ssml_gender=texttospeech.SsmlVoiceGender.MALE
        ))

    print(f"Spoken response: {response}")  # デバッグ用ログ
