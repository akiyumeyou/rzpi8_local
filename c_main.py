import os
import json
import asyncio
import requests
import csv
from datetime import datetime
import random
from google.cloud import texttospeech
from oauth2client.service_account import ServiceAccountCredentials
from c_text_to_speech import google_text_to_speech, elevenlabs_text_to_speech, play_audio
from c_speech_recognition import recognize_speech_from_mic
from c_file_operations import save_conversation_to_csv, run_js_summary_script, upload_csv_to_drive
from c_nod_response import play_nod_response, generate_custom_response
from subprocess import Popen, PIPE

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

# 初期設定のGoogle Cloud TTSの男性の声
google_voice_params = texttospeech.VoiceSelectionParams(
    language_code="ja-JP",
    name="ja-JP-Standard-A",
    ssml_gender=texttospeech.SsmlVoiceGender.MALE
)

# 初期メッセージ
initial_message = "今日は誰と話しますか？"

async def generate_ai_response(user_input, past_messages=[]):
    print("Generating response...")  # デバッグ用ログ
    result = await asyncio.to_thread(Popen,
        ['node', 'ap.js', user_input, json.dumps(past_messages)],
        stdout=PIPE,
        stderr=PIPE,
        text=True
    )
    stdout, stderr = result.communicate()

    if result.returncode != 0:
        print(f"Node.js script error: {stderr}")  # デバッグ用ログ
        raise Exception(f"Node.js script error: {stderr}")

    response_data = json.loads(stdout)
    print(f"Generated AI response: {response_data['responseMessage']}")  # デバッグ用ログ
    return response_data['responseMessage'], response_data['pastMessages']

async def main():
    past_messages = []
    conversations = []
    voice_id = google_voice_params  # 初期設定のGoogle Cloud TTSの男性の声
    custom_voice = False  # クローン音声の使用を示すフラグ

    print(f"Initial message: {initial_message}")  # デバッグ用ログ
    audio_content = await google_text_to_speech(initial_message, voice_id)
    await play_audio(audio_content)
    conversations.append(("システム", initial_message))
    print("Initial message spoken.")  # デバッグ用ログ

    speech = await recognize_speech_from_mic()
    print(f"User response: {speech}")  # デバッグ用ログ

    if "あなた" in speech:
        confirmation_message = "このまま男性の声で続けます。"
        audio_content = await google_text_to_speech(confirmation_message, voice_id)
        await play_audio(audio_content)
        print("Continuing with male voice.")  # デバッグ用ログ
    else:
        voice_id = "FeaM2xaHKiX1yiaPxvwe"
        custom_voice = True
        confirmation_message = "声を変更しました。"
        audio_content = await elevenlabs_text_to_speech(confirmation_message, voice_id)
        await play_audio(audio_content)
        print("Voice changed to female.")  # デバッグ用ログ

    conversations.append(("システム", confirmation_message))

    while True:
        speech = await recognize_speech_from_mic()
        print(f"User response: {speech}")  # デバッグ用ログ
        if speech:
            conversations.append(("ユーザー", speech))

            if "終了" in speech:
                print("Conversation ended by user.")  # デバッグ用ログ
                break

            # 70%の確率で相槌を挿入
            if random.random() < 0.7:
                await play_nod_response(custom_voice)

            # AIへの応答を生成
            response, past_messages = await generate_ai_response(speech, past_messages)

            print(f"Generated AI response: {response}")  # デバッグ用ログ

            if isinstance(voice_id, texttospeech.VoiceSelectionParams):
                audio_content = await google_text_to_speech(response, voice_id)
            else:
                audio_content = await elevenlabs_text_to_speech(response, voice_id)

            await play_audio(audio_content)
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
