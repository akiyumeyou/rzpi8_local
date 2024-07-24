import os
import json
import subprocess
import asyncio
from google.cloud import texttospeech
import sys
import csv
from datetime import datetime
import speech_recognition as sr
from oauth2client.service_account import ServiceAccountCredentials
import random

print("Starting script...")

# 環境変数の設定
if os.getenv('RUNNING_IN_DOCKER'):
    json_path = "/app/rzpi_chat.json"
else:
    json_path = "/Users/satouakiko/Desktop/PY/rzpi_chat.json"

os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = json_path
os.environ['SDL_AUDIODRIVER'] = 'coreaudio'  # MacOSではcoreaudioを使用

# Google Cloud Text-to-Speech API の初期化
try:
    client = texttospeech.TextToSpeechClient()
    print("Google Cloud Text-to-Speech client initialized successfully.")
except Exception as e:
    print(f"Failed to initialize Google Cloud Text-to-Speech client: {e}")

os.environ['VOSK_LOG_LEVEL'] = '0'
os.environ['PYTHONWARNINGS'] = 'ignore:ResourceWarning'
os.environ['PULSE_LOG'] = '0'

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

async def play_audio(filename, stop_event):
    try:
        # 音声再生を開始
        process = subprocess.Popen(['mpg123', filename])
        print("Playing audio...")

        # 音声再生中にユーザーの発話を検出するためのループ
        while process.poll() is None:
            if stop_event.is_set():
                process.terminate()
                print("Audio playback stopped due to user speech.")
                break
            await asyncio.sleep(0.1)

    except Exception as e:
        print(f"Error during audio playback: {e}")

async def recognize_speech_from_mic(mic_index, stop_event):
    recognizer = sr.Recognizer()
    microphone = sr.Microphone(device_index=mic_index)

    try:
        with microphone as source:
            recognizer.adjust_for_ambient_noise(source)
            print("Listening for speech...")  # デバッグ用ログ
            audio = await asyncio.to_thread(recognizer.listen, source)
            print("Audio captured")  # デバッグ用ログ

        if audio is None:
            print("No audio captured")
            raise Exception("No audio captured")

        recognized_text = recognizer.recognize_google(audio, language="ja-JP")
        print(f"Recognized: {recognized_text}")
        stop_event.set()  # 音声再生を停止するためにイベントを設定
        return recognized_text
    except sr.UnknownValueError:
        print("Google Speech Recognition could not understand audio")
        return ""
    except sr.RequestError as e:
        print(f"Could not request results from Google Speech Recognition service; {e}")
        return ""
    except AttributeError as e:
        print(f"AttributeError: {e}")
        return ""
    except Exception as e:
        print(f"Error recognizing speech: {e}")
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

async def check_if_finished(user_speech):
    print("Checking if speech is finished...")
    result = await asyncio.to_thread(subprocess.run,
        ['node', 'check.js'],
        input=json.dumps({"userSpeech": user_speech}),
        capture_output=True,
        text=True
    )

    if result.returncode != 0:
        print(f"Node.js script error: {result.stderr}")
        raise Exception(f"Node.js script error: {result.stderr}")

    check_data = json.loads(result.stdout)
    return check_data['isFinished']

async def text_to_speech(text, stop_event):
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

        # 音声再生
        await play_audio(filename, stop_event)
        os.remove(filename)
    except Exception as e:
        print(f"Error during audio playback: {e}")

async def play_nod_response(stop_event):
    nod_file = random.choice(nod_responses)
    print(f"Playing nod response: {nod_file}")
    if not os.path.exists(nod_file):
        print(f"File not found: {nod_file}")
        return

    await play_audio(nod_file, stop_event)

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

    stop_event = asyncio.Event()
    await text_to_speech(initial_message, stop_event)
    conversations.append(("システム", initial_message))
    print("Initial message spoken.")

    mic_index = 0  # 使用するマイクのインデックス

    while True:
        print("Waiting for user's speech...")
        stop_event.clear()
        recognize_task = asyncio.create_task(recognize_speech_from_mic(mic_index, stop_event))
        
        speech = await recognize_task
        print(f"Speech recognized: {speech}")

        if speech:
            conversations.append(("ユーザー", speech))

            if "終了" in speech:
                print("Conversation ended by user.")
                break

            is_finished_task = asyncio.create_task(check_if_finished(speech))
            is_finished = await is_finished_task
            print(f"Is finished: {is_finished}")

            if not is_finished:
                continue  # ユーザーの発話が続いている場合は応答を生成せずに再度音声認識

            if random.random() < 0.9:
                stop_event.clear()
                await play_nod_response(stop_event)

            response_task = asyncio.create_task(generate_response(speech, past_messages))
            response, past_messages = await response_task
            print(f"AI response: {response}")

            response_ok_task = asyncio.create_task(check_response_appropriateness(speech, response))
            response_ok = await response_ok_task
            print(f"Response appropriate: {response_ok}")

            if response_ok:
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
            print("Failed to upload to Google Drive: Operation timed out")

if __name__ == "__main__":
    print("Starting main function...")
    asyncio.run(main())
