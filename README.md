# Route Cafe Bot

京王線・小田急線の経路上で、途中駅の最寄りカフェを探すタスク指向型対話システムです。

## Features

- フレーム型対話管理で、出発駅・到着駅・利用目的・利用時刻をスロットとして保持
- 京王線・小田急線に限定した路線グラフで乗り換えを考慮
- 駅情報は HeartRails Express API / ekidata.jp API を利用
- カフェ情報は HotPepper Gourmet API を利用
- 経路図、駅リスト、駅別カフェ候補をUIに表示

## APIs

- HeartRails Express API: 駅名・路線・緯度経度
- ekidata.jp API: 駅一覧の代替取得
- HotPepper Gourmet API: 駅周辺のカフェ候補
- OpenAI API: ユーザ発話からスロット抽出、推薦文生成

## Setup

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install fastapi uvicorn python-dotenv openai requests
cp .env.example .env
```

`backend/.env` にAPIキーを設定します。

```bash
uvicorn main:app --reload
```

別ターミナルでフロントエンドを起動します。

```bash
cd frontend
npm install
npm run dev
```

バックエンドを `8000` 以外で起動する場合は、フロントエンド起動時にAPI URLを指定します。

```bash
VITE_API_BASE_URL=http://127.0.0.1:8001 npm run dev
```

## Example

```text
新宿から善行まで、作業できるカフェを今日18時に使いたい
```

```text
調布から下北沢まで、友達と休憩できるカフェを今探して
```
