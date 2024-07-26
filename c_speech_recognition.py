import asyncio
import speech_recognition as sr

async def recognize_speech_from_mic():
    recognizer = sr.Recognizer()
    microphone = sr.Microphone()

    with microphone as source:
        recognizer.adjust_for_ambient_noise(source)
        audio = await asyncio.to_thread(recognizer.listen, source)

    try:
        recognized_text = await asyncio.to_thread(recognizer.recognize_google, audio, language="ja-JP")
        return recognized_text
    except sr.UnknownValueError:
        return ""
    except sr.RequestError as e:
        return ""
