# ベースイメージとしてPython 3.9-slimを使用
FROM python:3.9-slim

# システムの依存関係をインストール
RUN apt-get update && apt-get install -y \
    build-essential \
    libfreetype6-dev \
    libsdl2-dev \
    libsdl2-image-dev \
    libsdl2-mixer-dev \
    libsdl2-ttf-dev \
    libavformat-dev \
    libavcodec-dev \
    libswscale-dev \
    && rm -rf /var/lib/apt/lists/*

# 作業ディレクトリを設定
WORKDIR /app

# requirements.txtをコンテナにコピー
COPY requirements.txt .

# requirements.txtに基づいてPythonパッケージをインストール
RUN pip install --no-cache-dir -r requirements.txt

# プロジェクトのすべてのファイルをコンテナにコピー
COPY . .

# JSON認証ファイルをコンテナにコピー
COPY rzpi_chat.json /app/rzpi_chat.json

# 環境変数を設定
ENV GOOGLE_APPLICATION_CREDENTIALS="/app/rzpi_chat.json"
ENV RUNNING_IN_DOCKER=true

# コンテナが起動する際に実行するコマンドを設定
CMD ["python", "aichat.py"]
