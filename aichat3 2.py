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

async def recognize_speech_from_mic():
    recognizer = sr.Recognizer()
    microphone = sr.Microphone()

    with microphone as source:
        recognizer.adjust_for_ambient_noise(source)
        print("Listening for speech...")
        audio = await asyncio.to_thread(recognizer.listen, source)

    try:
        recognized_text = await asyncio.to_thread(recognizer.recognize_google, audio, language="ja-JP")
        print(f"Recognized: {recognized_text}")
        return recognized_text
    except sr.UnknownValueError:
        print("Google Speech Recognition could not understand audio")
        return ""
    except sr.RequestError as e:
        print(f"Could not request results from Google Speech Recognition service; {e}")
        return ""

async def generate_response(prompt, past_messages=[]):
    print("Generating response...")
    result = await asyncio.to_thread(subprocess.run,
        ['node', 'ap.js', prompt, json.dumps(past_messages)],
        capture_output=True,
        text=True
    )

    if result.returncode != 0:
        print(f"Node.js script error: {result.stderr}")
        raise Exception(f"Node.js script error: {result.stderr}")

    response_data = json.loads(result.stdout)
    print(f"Generated response: {response_data['responseMessage']}")
    return response_data['responseMessage'], response_data['pastMessages']

async def check_response_appropriateness(user_speech, ai_response):
    print("Checking response appropriateness...")
    result = await asyncio.to_thread(subprocess.run,
        ['node', 'check.js'],
        input=json.dumps({"userSpeech": user_speech, "aiResponse": ai_response}),
        capture_output=True,
        text=True
    )

    if result.returncode != 0:
        print(f"Node.js script error: {result.stderr}")
        raise Exception(f"Node.js script error: {result.stderr}")

    response_check_data = json.loads(result.stdout)
    return response_check_data['responseOk']

async def text_to_speech(text):
    print(f"Converting text to speech: {text}")
    synthesis_input = texttospeech.SynthesisInput(text=text)

    voice = texttospeech.VoiceSelectionParams(
        language_code="ja-JP",
        name="ja-JP-Standard-C",
        ssml_gender=texttospeech.SsmlVoiceGender.MALE
    )

    audio_config = texttospeech.AudioConfig(
        audio_encoding=texttospeech.AudioEncoding.MP3
    )

    try:
        response = client.synthesize_speech(
            input=synthesis_input, voice=voice, audio_config=audio_config
        )
        print("Text-to-Speech synthesis successful.")
    except Exception as e:
        print(f"Text-to-Speech synthesis failed: {e}")
        return

    filename = "response.mp3"
    try:
        with open(filename, "wb") as out:
            out.write(response.audio_content)
        print(f"Audio content written to {filename}")

        pygame.mixer.init()
        pygame.mixer.music.load(filename)
        pygame.mixer.music.play()
        print("Playing audio...")

        while pygame.mixer.music.get_busy():
            await asyncio.sleep(0.1)

        print("Audio playback finished.")
        os.remove(filename)
    except Exception as e:
        print(f"Error during audio playback: {e}")

async def play_nod_response():
    nod_file = random.choice(nod_responses)
    print(f"Playing nod response: {nod_file}")
    if not os.path.exists(nod_file):
        print(f"File not found: {nod_file}")
        return

    pygame.mixer.init()
    pygame.mixer.music.load(nod_file)
    pygame.mixer.music.play()
    
    while pygame.mixer.music.get_busy():
        await asyncio.sleep(0.1)

def save_conversation_to_csv(conversations):
    now = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = "chat.csv"
    try:
        with open(filename, mode='w', newline='', encoding='utf-8') as file:
            writer = csv.writer(file)
            writer.writerow(["User", "AI"])
            writer.writerows(conversations)
        print(f"Saved CSV to {filename}")
    except Exception as e:
        print(f"Failed to save CSV: {e}")
    return filename

def run_js_summary_script(csv_filename):
    try:
        print(f"Running summary script for {csv_filename}")
        result = subprocess.run(
            ['node', 'sum.js', csv_filename],
            capture_output=True,
            text=True
        )
        if result.returncode != 0:
            print(f"Node.js script error: {result.stderr}")
            raise Exception(f"Node.js script error: {result.stderr}")

        print(f"Node.js script output: {result.stdout}")
        return result.stdout.strip()
    except Exception as e:
        print(f"Failed to run JS script: {e}")
        return None

async def upload_csv_to_drive(local_csv_path, file_name, folder_id=None):
    try:
        print(f"Uploading {local_csv_path} to Google Drive as {file_name}")
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
        
        print(f"File '{file_name}' uploaded to Google Drive")
    except Exception as e:
        print(f"Failed to upload to Google Drive: {e}")

async def main():
    past_messages = []
    conversations = []

    initial_message = "こんにちは、お話しできますか？"
    print(f"Initial message: {initial_message}")

    await text_to_speech(initial_message)
    conversations.append(("システム", initial_message))
    print("Initial message spoken.")

    while True:
        recognize_task = asyncio.create_task(recognize_speech_from_mic())
        await asyncio.sleep(0.1)  # 短い待機時間を設けて発話の終了を検知

        speech = await recognize_task

        if speech:
            conversations.append(("ユーザー", speech))

            if "終了" in speech:
                print("Conversation ended by user.")
                break

            if random.random() < 0.9:
                await play_nod_response()

            response_task = asyncio.create_task(generate_response(speech, past_messages))
            response, past_messages = await response_task

            response_ok_task = asyncio.create_task(check_response_appropriateness(speech, response))
            response_ok = await response_ok_task

            if response_ok:
                await text_to_speech(response)
                conversations.append(("AI", response))

    csv_file = save_conversation_to_csv(conversations)
    summary = run_js_summary_script(csv_file)

    if summary:
        now = datetime.now().strftime("%Y%m%d_%H%M%S")
        try:
            await asyncio.wait_for(upload_csv_to_drive("chat.csv", f"chat_{now}.csv", "1cwD7MZtll76L5rWFpRb7-egTwN0g26bG"), timeout=30.0)
        except asyncio.TimeoutError:
            print("Failed to upload to Google Drive: Operation timed out")

if __name__ == "__main__":
    print("Starting main function...")
    asyncio.run(main())
