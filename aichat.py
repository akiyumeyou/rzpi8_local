import os
import json
import subprocess
import asyncio
import pygame
from google.cloud import texttospeech
import sys
import csv
from datetime import datetime
import speech_recognition as sr
from pydrive.auth import GoogleAuth
from pydrive.drive import GoogleDrive
from oauth2client.service_account import ServiceAccountCredentials
import random

# デバッグ用のログメッセージ
print("Starting script...")

# 環境変数の設定（Docker内とローカル環境のパスに対応）
if os.getenv('RUNNING_IN_DOCKER'):
    json_path = "/app/rzpi_chat.json"
else:
    json_path = "/Users/satouakiko/Desktop/PY/rzpi_chat.json"

os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = json_path

# Google Cloud Text-to-Speech API の初期化
try:
    client = texttospeech.TextToSpeechClient()
    print("Google Cloud Text-to-Speech client initialized successfully.")
except Exception as e:
    print(f"Failed to initialize Google Cloud Text-to-Speech client: {e}")

# Google Drive API の認証情報設定
SERVICE_ACCOUNT_FILE = json_path
SCOPES = ['https://www.googleapis.com/auth/drive']
try:
    creds = ServiceAccountCredentials.from_json_keyfile_name(SERVICE_ACCOUNT_FILE, SCOPES)
    print("Google Drive credentials initialized successfully.")
except Exception as e:
    print(f"Failed to initialize Google Drive credentials: {e}")

# VOSKのログレベルを抑制
os.environ['VOSK_LOG_LEVEL'] = '0'

# ALSAのエラーメッセージを抑制
os.environ['PYTHONWARNINGS'] = 'ignore:ResourceWarning'
os.environ['PULSE_LOG'] = '0'

# MacOSではcoreaudioを使用
os.environ['SDL_AUDIODRIVER'] = 'coreaudio'

# 事前録音した相槌の音声ファイル
nod_responses = ["hoo.mp3", "naruhodo.mp3", "hee.mp3"]

# 応答ルールの定義
response_rules = {
    "endings": {
        "です。": "そうなんですね。",
        "だよ。": "なるほど。",
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

async def recognize_speech_from_mic(stop_event):
    recognizer = sr.Recognizer()
    microphone = sr.Microphone()

    with microphone as source:
        recognizer.adjust_for_ambient_noise(source)
        print("Listening for speech...")  # デバッグ用ログ
        audio = await asyncio.to_thread(recognizer.listen, source)

    try:
        recognized_text = await asyncio.to_thread(recognizer.recognize_google, audio, language="ja-JP")
        print(f"Recognized: {recognized_text}")  # デバッグ用ログ
        stop_event.set()  # 音声認識が成功したらイベントを設定して音声再生を停止
        return recognized_text
    except sr.UnknownValueError:
        print("Google Speech Recognition could not understand audio")  # デバッグ用ログ
        return ""
    except sr.RequestError as e:
        print(f"Could not request results from Google Speech Recognition service; {e}")  # デバッグ用ログ
        return ""

async def generate_response(prompt, past_messages=[]):
    print("Generating response...")  # デバッグ用ログ
    result = await asyncio.to_thread(subprocess.run,
        ['node', 'ap.js', prompt, json.dumps(past_messages)],
        capture_output=True,
        text=True
    )

    if result.returncode != 0:
        print(f"Node.js script error: {result.stderr}")  # デバッグ用ログ
        raise Exception(f"Node.js script error: {result.stderr}")

    response_data = json.loads(result.stdout)
    print(f"Generated response: {response_data['responseMessage']}")  # デバッグ用ログ
    return response_data['responseMessage'], response_data['pastMessages']

async def text_to_speech(text, stop_event):
    print(f"Converting text to speech: {text}")  # デバッグ用ログ
    synthesis_input = texttospeech.SynthesisInput(text=text)

    voice = texttospeech.VoiceSelectionParams(
        language_code="ja-JP",
        name="ja-JP-Standard-C",  # 男性の声
        ssml_gender=texttospeech.SsmlVoiceGender.MALE
    )

    audio_config = texttospeech.AudioConfig(
        audio_encoding=texttospeech.AudioEncoding.MP3
    )

    try:
        response = client.synthesize_speech(
            input=synthesis_input, voice=voice, audio_config=audio_config
        )
        print("Text-to-Speech synthesis successful.")  # デバッグ用ログ
    except Exception as e:
        print(f"Text-to-Speech synthesis failed: {e}")  # デバッグ用ログ
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
            if stop_event.is_set():
                pygame.mixer.music.stop()
                break
            await asyncio.sleep(0.1)

        print("Audio playback finished.")  # デバッグ用ログ
        os.remove(filename)
    except Exception as e:
        print(f"Error during audio playback: {e}")  # デバッグ用ログ

async def play_nod_response(stop_event):
    nod_file = random.choice(nod_responses)
    print(f"Playing nod response: {nod_file}")  # デバッグ用ログ
    if not os.path.exists(nod_file):
        print(f"File not found: {nod_file}")  # エラーログ
        return

    pygame.mixer.init()
    pygame.mixer.music.load(nod_file)
    pygame.mixer.music.play()
    
    while pygame.mixer.music.get_busy():
        if stop_event.is_set():
            pygame.mixer.music.stop()
            break
        await asyncio.sleep(0.1)

def get_aizuchi(text):
    for ending, response in response_rules["endings"].items():
        if text.endswith(ending):
            return response
    
    for keyword, response in response_rules["keywords"].items():
        if keyword in text:
            return response
    
    return ""

def save_conversation_to_csv(conversations):
    now = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = "chat.csv"  # ローカルに保存するファイルは chat.csv に固定
    try:
        with open(filename, mode='w', newline='', encoding='utf-8') as file:
            writer = csv.writer(file)
            writer.writerow(["User", "AI"])
            writer.writerows(conversations)
        print(f"Saved CSV to {filename}")  # デバッグ用ログ
    except Exception as e:
        print(f"Failed to save CSV: {e}")  # デバッグ用ログ
    return filename

def run_js_summary_script(csv_filename):
    try:
        print(f"Running summary script for {csv_filename}")  # デバッグ用ログ
        result = subprocess.run(
            ['node', 'sum.js', csv_filename],
            capture_output=True,
            text=True
        )
        if result.returncode != 0:
            print(f"Node.js script error: {result.stderr}")  # デバッグ用ログ
            raise Exception(f"Node.js script error: {result.stderr}")

        print(f"Node.js script output: {result.stdout}")  # デバッグ用ログ
        return result.stdout.strip()  # 要約結果を返す
    except Exception as e:
        print(f"Failed to run JS script: {e}")  # デバッグ用ログ
        return None

async def upload_csv_to_drive(local_csv_path, file_name, folder_id=None):
    try:
        print(f"Uploading {local_csv_path} to Google Drive as {file_name}")  # デバッグ用ログ
        scope = ['https://www.googleapis.com/auth/drive']
        credentials = ServiceAccountCredentials.from_json_keyfile_name(SERVICE_ACCOUNT_FILE, scope)

        gauth = GoogleAuth()
        gauth.credentials = credentials

        drive = GoogleDrive(gauth)
        
        file_metadata = {'title': file_name}
        if folder_id:
            file_metadata['parents'] = [{'id': folder_id}]
        
        file = drive.CreateFile(file_metadata)
        file.SetContentFile(local_csv_path)
        file.Upload()
        
        print(f"File '{file_name}' uploaded to Google Drive")  # デバッグ用ログ
    except Exception as e:
        print(f"Failed to upload to Google Drive: {e}")  # デバッグ用ログ

async def main():
    past_messages = []
    conversations = []

    initial_message = "こんにちは、お話しできますか？"
    print(f"Initial message: {initial_message}")  # デバッグ用ログ

    stop_event = asyncio.Event()
    await text_to_speech(initial_message, stop_event)
    conversations.append(("システム", initial_message))
    print("Initial message spoken.")  # デバッグ用ログ

    while True:
        stop_event.clear()
        recognize_task = asyncio.create_task(recognize_speech_from_mic(stop_event))
        
        speech = await recognize_task

        if speech:
            conversations.append(("ユーザー", speech))

            if "終了" in speech:
                print("Conversation ended by user.")  # デバッグ用ログ
                break

            # 90%の確率で相槌を挿入
            if random.random() < 0.9:
                aizuchi = get_aizuchi(speech)
                if aizuchi:
                    await play_nod_response(stop_event)
                    stop_event.clear()
                    await text_to_speech(aizuchi, stop_event)

            response_task = asyncio.create_task(generate_response(speech, past_messages))
            response, past_messages = await response_task

            stop_event.clear()
            await text_to_speech(response, stop_event)
            conversations.append(("AI", response))

    csv_file = save_conversation_to_csv(conversations)
    summary = run_js_summary_script(csv_file)

    if summary:
        now = datetime.now().strftime("%Y%m%d_%H%M%S")
        try:
            await asyncio.wait_for(upload_csv_to_drive("chat.csv", f"chat_{now}.csv", "1cwD7MZtll76L5rWFpRb7-egTwN0g26bG"), timeout=30.0)
        except asyncio.TimeoutError:
            print("Failed to upload to Google Drive: Operation timed out")  # タイムアウトエラーログ

if __name__ == "__main__":
    print("Starting main function...")  # デバッグ用ログ
    asyncio.run(main())
