import csv
from datetime import datetime
import subprocess
from pydrive.auth import GoogleAuth
from pydrive.drive import GoogleDrive
from oauth2client.service_account import ServiceAccountCredentials

SERVICE_ACCOUNT_FILE = "rzpi_chat.json"

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
        # 認証情報の読み込み
        scope = ['https://www.googleapis.com/auth/drive']
        credentials = ServiceAccountCredentials.from_json_keyfile_name(SERVICE_ACCOUNT_FILE, scope)

        gauth = GoogleAuth()
        gauth.credentials = credentials

        drive = GoogleDrive(gauth)

        # 新しいファイルを作成し、CSVファイルの内容を設定
        file_metadata = {'title': file_name}
        if folder_id:
            file_metadata['parents'] = [{'id': folder_id}]

        file = drive.CreateFile(file_metadata)
        file.SetContentFile(local_csv_path)

        # ファイルをGoogle Driveにアップロード
        file.Upload()

        print(f"File '{file_name}' uploaded to Google Drive")  # デバッグ用ログ
    except Exception as e:
        print(f"Failed to upload to Google Drive: {e}")  # デバッグ用ログ
