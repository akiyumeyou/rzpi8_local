import random
from pydub import AudioSegment
from pydub.playback import play

nod_responses = ["hoo.mp3", "naruhodo.mp3", "hee.mp3"]

async def play_nod_response(custom_voice=False):
    if custom_voice:
        nod_responses_custom = [f"{resp.split('.')[0]}_c.mp3" for resp in nod_responses]
        nod_file = random.choice(nod_responses_custom)
    else:
        nod_file = random.choice(nod_responses)
    
    try:
        audio = AudioSegment.from_file(nod_file, format="mp3")
        play(audio)
    except Exception as e:
        print(f"Error playing nod response: {e}")

async def generate_custom_response(user_input, custom_voice):
    endings = {
        "です。": "そうなんですね。",
        "ました。": "へえ、そうなんですね。",
        "だったんですよ。": "ほー、それは興味深いですね。",
        "ます。": "そうですね。"
    }
    keywords = {
        "困っています": "それは大変ですね。",
        "好きです": "うんうん、私も好きです。",
        "嫌い": "それは残念ですね。",
        "楽しい": "それは楽しいですね。",
        "嬉しい": "それは嬉しいですね。",
        "悲しい": "それは悲しいですね。",
        "辛い": "それは辛いですね。"
    }

    for ending, response in endings.items():
        if user_input.endswith(ending):
            return response

    for keyword, response in keywords.items():
        if keyword in user_input:
            return response

    return "そうなんですね。"
