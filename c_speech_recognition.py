import speech_recognition as sr
import asyncio

async def recognize_speech_from_mic():
    recognizer = sr.Recognizer()
    microphone = sr.Microphone()

    with microphone as source:
        recognizer.adjust_for_ambient_noise(source)
        print("Listening for speech...")  # デバッグ用ログ
        audio = await asyncio.to_thread(recognizer.listen, source)

    try:
        recognized_text = await asyncio.to_thread(recognizer.recognize_google, audio, language="ja-JP")
        print(f"Recognized: {recognized_text}")  # デバッグ用ログ
        return recognized_text
    except sr.UnknownValueError:
        print("Google Speech Recognition could not understand audio")  # デバッグ用ログ
        return ""
    except sr.RequestError as e:
        print(f"Could not request results from Google Speech Recognition service; {e}")  # デバッグ用ログ
        return ""
