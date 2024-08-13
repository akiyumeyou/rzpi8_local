import os
import json
import asyncio
import random
from datetime import datetime
from google.cloud import texttospeech
from oauth2client.service_account import ServiceAccountCredentials
from c_text_to_speech import google_text_to_speech, elevenlabs_text_to_speech, play_audio, stop_audio
from c_speech_recognition import recognize_speech_from_mic
from c_file_operations import save_conversation_to_csv, run_js_summary_script, upload_csv_to_drive
from c_nod_response import play_nod_response
from subprocess import Popen, PIPE

# 環境変数の設定
if os.getenv('RUNNING_IN_DOCKER'):
    json_path = "/app/rzpi_chat.json"
else:
    json_path = "/Users/satouakiko/Desktop/PY/rzpi_chat.json"

os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = json_path

# Google Cloud Text-to-Speech API の初期化
client = texttospeech.TextToSpeechClient()

# Google Drive API の認証情報設定
SERVICE_ACCOUNT_FILE = json_path
SCOPES = ['https://www.googleapis.com/auth/drive']
creds = ServiceAccountCredentials.from_json_keyfile_name(SERVICE_ACCOUNT_FILE, SCOPES)

# 初期設定のGoogle Cloud TTSの男性の声
google_voice_params_male = texttospeech.VoiceSelectionParams(
    language_code="ja-JP",
    name="ja-JP-Standard-C",
    ssml_gender=texttospeech.SsmlVoiceGender.MALE
)

google_voice_params_female = texttospeech.VoiceSelectionParams(
    language_code="ja-JP",
    name="ja-JP-Standard-A",
    ssml_gender=texttospeech.SsmlVoiceGender.FEMALE
)

# 初期メッセージ
initial_message = "今日は誰と話しますか？"

async def generate_ai_response(user_input, past_messages=[]):
    process = await asyncio.create_subprocess_exec(
        'node', 'ap.js', user_input, json.dumps(past_messages),
        stdout=PIPE,
        stderr=PIPE
    )
    stdout, stderr = await process.communicate()

    if process.returncode != 0:
        raise Exception(f"Node.js script error: {stderr.decode()}")

    response_data = json.loads(stdout.decode())
    return response_data['responseMessage'], response_data['pastMessages']

async def main():
    past_messages = []
    conversations = []
    voice_id = google_voice_params_male
    custom_voice = False

    print(f"Initial message: {initial_message}")
    audio_content = await google_text_to_speech(initial_message, voice_id)
    await play_audio(audio_content)
    conversations.append(("システム", initial_message))
    print("Initial message spoken.")

    # 両方の声を事前に読み込む
    await elevenlabs_text_to_speech("準備完了", "FeaM2xaHKiX1yiaPxvwe")
    await google_text_to_speech("準備完了", google_voice_params_female)

    voice_changed = False

    while True:
        speech = await recognize_speech_from_mic()
        print(f"User response: {speech}")
        if speech:
            conversations.append(("ユーザー", speech))

            if "終了" in speech:
                print("Conversation ended by user.")
                break

            if "別の人" in speech and not voice_changed:
                voice_id = "FeaM2xaHKiX1yiaPxvwe"
                custom_voice = True
                voice_changed = True
            elif not voice_changed:
                voice_id = google_voice_params_male
                custom_voice = False
                voice_changed = True

            # AI応答と相槌の非同期処理
            nod_task = None
            if random.random() < 0.7:
                nod_task = asyncio.create_task(play_nod_response(custom_voice))

            response, past_messages = await generate_ai_response(speech, past_messages)
            print(f"Generated AI response: {response}")

            # 音声再生中にユーザーが話し始めたら再生を停止
            stop_audio()

            if isinstance(voice_id, texttospeech.VoiceSelectionParams):
                audio_content = await google_text_to_speech(response, voice_id)
            else:
                audio_content = await elevenlabs_text_to_speech(response, voice_id)

            if nod_task:
                await nod_task

            await play_audio(audio_content)
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
