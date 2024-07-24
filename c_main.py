import asyncio
import random
from c_speech_recognition import recognize_speech_from_mic
from c_text_to_speech import google_text_to_speech, elevenlabs_text_to_speech
from c_nod_response import play_nod_response, generate_custom_response
from c_file_operations import save_conversation_to_csv, run_js_summary_script, upload_csv_to_drive
from google.cloud import texttospeech

async def main():
    past_messages = []
    conversations = []
    google_voice_params = texttospeech.VoiceSelectionParams(
        language_code="ja-JP",
        name="ja-JP-Standard-C",  # 男性の声
        ssml_gender=texttospeech.SsmlVoiceGender.MALE
    )
    voice_id = google_voice_params  # 初期設定のGoogle Cloud TTSの男性の声
    custom_voice = False  # クローン音声の使用を示すフラグ

    initial_message = "今日は誰と話しますか？"
    print(f"Initial message: {initial_message}")  # デバッグ用ログ
    await google_text_to_speech(initial_message, voice_id)
    conversations.append(("システム", initial_message))
    print("Initial message spoken.")  # デバッグ用ログ

    speech = await recognize_speech_from_mic()
    print(f"User response: {speech}")  # デバッグ用ログ

    if "あなた" in speech:
        confirmation_message = "このまま男性の声で続けます。"
        await google_text_to_speech(confirmation_message, voice_id)
        print("Continuing with male voice.")  # デバッグ用ログ
    else:
        voice_id = "FeaM2xaHKiX1yiaPxvwe"  # 女性の声のIDを設定
        custom_voice = True
        confirmation_message = "声を変更しました。"
        await elevenlabs_text_to_speech(confirmation_message, voice_id)
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

            if random.random() < 0.7:
                await play_nod_response(custom_voice)
            else:
                response = await generate_custom_response(speech, custom_voice)
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
