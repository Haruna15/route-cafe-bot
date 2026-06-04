import os
import json
from collections import deque
from pathlib import Path
from dotenv import load_dotenv

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from openai import OpenAI
import requests
import re

load_dotenv(Path(__file__).with_name(".env"))

openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

conversation_slots = {
    "from_station": None,
    "to_station": None,
    "purpose": None,
    "time": None,
}

LINE_CODES = {
    "小田急小田原線": "25001",
    "小田急江ノ島線": "25002",
    "小田急多摩線": "25003",
    "京王線": "24001",
    "京王相模原線": "24002",
    "京王井の頭線": "24006",
}

FALLBACK_LINES = {
    "小田急小田原線": [
        "新宿", "南新宿", "参宮橋", "代々木八幡", "代々木上原", "東北沢", "下北沢",
        "世田谷代田", "梅ヶ丘", "豪徳寺", "経堂", "千歳船橋", "祖師ヶ谷大蔵",
        "成城学園前", "喜多見", "狛江", "和泉多摩川", "登戸", "向ヶ丘遊園", "生田",
        "読売ランド前", "百合ヶ丘", "新百合ヶ丘", "柿生", "鶴川", "玉川学園前",
        "町田", "相模大野", "小田急相模原", "相武台前", "座間", "海老名", "厚木",
        "本厚木", "愛甲石田", "伊勢原", "鶴巻温泉", "東海大学前", "秦野", "渋沢",
        "新松田", "開成", "栢山", "富水", "螢田", "足柄", "小田原",
    ],
    "小田急江ノ島線": [
        "相模大野", "東林間", "中央林間", "南林間", "鶴間", "大和", "桜ヶ丘",
        "高座渋谷", "長後", "湘南台", "六会日大前", "善行", "藤沢本町", "藤沢",
        "本鵠沼", "鵠沼海岸", "片瀬江ノ島",
    ],
    "小田急多摩線": [
        "新百合ヶ丘", "五月台", "栗平", "黒川", "はるひ野", "小田急永山",
        "小田急多摩センター", "唐木田",
    ],
    "京王線": [
        "新宿", "笹塚", "代田橋", "明大前", "下高井戸", "桜上水", "上北沢",
        "八幡山", "芦花公園", "千歳烏山", "仙川", "つつじヶ丘", "柴崎", "国領",
        "布田", "調布", "西調布", "飛田給", "武蔵野台", "多磨霊園", "東府中",
        "府中", "分倍河原", "中河原", "聖蹟桜ヶ丘", "百草園", "高幡不動",
        "南平", "平山城址公園", "長沼", "北野", "京王八王子",
    ],
    "京王相模原線": [
        "調布", "京王多摩川", "京王稲田堤", "京王よみうりランド", "稲城",
        "若葉台", "京王永山", "京王多摩センター", "京王堀之内", "南大沢",
        "多摩境", "橋本",
    ],
    "京王井の頭線": [
        "渋谷", "神泉", "駒場東大前", "池ノ上", "下北沢", "新代田", "東松原",
        "明大前", "永福町", "西永福", "浜田山", "高井戸", "富士見ヶ丘", "久我山",
        "三鷹台", "井の頭公園", "吉祥寺",
    ],
}

TRANSFER_PAIRS = [
    ("京王多摩センター", "小田急多摩センター"),
    ("京王永山", "小田急永山"),
]

station_api_cache = None


class ChatRequest(BaseModel):
    message: str


@app.get("/")
def read_root():
    return {"message": "Route Cafe Bot backend is running"}


def ask_openai(prompt: str, json_only: bool = False):
    messages = []

    if json_only:
        messages.append({
            "role": "system",
            "content": "必ずJSONのみを返してください。説明文やMarkdownは不要です。"
        })

    messages.append({
        "role": "user",
        "content": prompt
    })

    response = openai_client.chat.completions.create(
        model="gpt-4o-mini",
        messages=messages,
    )

    return response.choices[0].message.content.strip()


def search_hotpepper_cafes(station_name: str, purpose: str = ""):
    api_key = os.getenv("HOTPEPPER_API_KEY")

    url = "https://webservice.recruit.co.jp/hotpepper/gourmet/v1/"
    keyword = f"{station_name} カフェ"

    params = {
        "key": api_key,
        "keyword": keyword,
        "count": 8,
        "format": "json",
    }

    response = requests.get(url, params=params, timeout=10)
    data = response.json()

    shops = data.get("results", {}).get("shop", [])

    cafes = []

    for shop in shops:
        cafes.append({
            "station": station_name,
            "name": shop.get("name"),
            "address": shop.get("address"),
            "access": shop.get("access"),
            "open": shop.get("open"),
            "url": shop.get("urls", {}).get("pc"),
            "catch": shop.get("catch"),
            "genre": shop.get("genre", {}).get("name"),
            "budget": shop.get("budget", {}).get("name"),
        })

    return cafes


def generate_recommendation(station_name: str, purpose: str, time: str, cafes: list):
    cafe_text = ""

    for i, cafe in enumerate(cafes[:5], start=1):
        cafe_text += f"""
候補{i}
店名: {cafe.get("name")}
ジャンル: {cafe.get("genre")}
予算: {cafe.get("budget")}
キャッチコピー: {cafe.get("catch")}
住所: {cafe.get("address")}
アクセス: {cafe.get("access")}
営業時間: {cafe.get("open")}
URL: {cafe.get("url")}
"""

    prompt = f"""
あなたはカフェ推薦を行う対話システムです。

利用者は、{station_name}駅周辺で、
{time}頃に、{purpose}目的で使えるカフェを探しています。

以下の候補店から、利用目的と店舗特徴を比較し、最も目的に合うカフェを3件選び、
日本語で自然に推薦してください。

条件:
- 最大3件推薦する
- できれば異なる途中駅から選ぶ
- 途中駅が少ない場合や候補が少ない場合は同じ駅でもよい
- 各店舗について、店名、駅名、理由、営業時間、URLを書く
- 利用時刻に営業していない可能性が高い店舗は推薦しない
- 営業時間が不明な場合は「営業時間は要確認」と書く

候補店:
{cafe_text}
"""

    return ask_openai(prompt)


def normalize_station_name(name: str):
    if not name:
        return ""
    name = name.strip()
    name = re.sub(r"(駅|えき)$", "", name)
    return name.replace("ケイオウ", "京王").replace("小田急線", "")


def get_line_stations_from_heartrails(line_name: str):
    url = "https://express.heartrails.com/api/json"
    params = {
        "method": "getStations",
        "line": line_name,
    }
    response = requests.get(url, params=params, timeout=10)
    data = response.json()
    stations = data.get("response", {}).get("station", [])

    result = []
    for station in stations:
        result.append({
            "name": normalize_station_name(station.get("name")),
            "lat": float(station["y"]) if station.get("y") else None,
            "lon": float(station["x"]) if station.get("x") else None,
        })

    return result


def get_line_stations_from_ekidata(line_cd: str):
    url = f"https://www.ekidata.jp/api/l/{line_cd}.json"
    response = requests.get(url, timeout=10)
    text = response.text.strip()

    match = re.search(r"xml\.data\s*=\s*(.*);", text, re.DOTALL)

    if not match:
        return []

    data = json.loads(match.group(1))
    stations = data.get("station_l", [])

    result = []
    for station in stations:
        result.append({
            "name": normalize_station_name(station.get("station_name")),
            "lat": float(station["lat"]) if station.get("lat") else None,
            "lon": float(station["lon"]) if station.get("lon") else None,
        })

    return result


def get_supported_station_data():
    global station_api_cache
    if station_api_cache is not None:
        return station_api_cache

    data = {}

    for line_name, line_cd in LINE_CODES.items():
        try:
            stations = get_line_stations_from_heartrails(line_name)
        except Exception:
            stations = []

        if not stations:
            try:
                stations = get_line_stations_from_ekidata(line_cd)
            except Exception:
                stations = []

        if not stations:
            stations = [{"name": name, "lat": None, "lon": None} for name in FALLBACK_LINES[line_name]]

        # ekidata can include branch or naming differences; fallback order keeps demos stable.
        if len(stations) < 2:
            stations = [{"name": name, "lat": None, "lon": None} for name in FALLBACK_LINES[line_name]]

        data[line_name] = stations

    station_api_cache = data
    return data


def build_railway_graph():
    graph = {}
    station_meta = {}
    line_data = get_supported_station_data()

    for line_name, stations in line_data.items():
        names = [station["name"] for station in stations if station.get("name")]

        for station in stations:
            name = station["name"]
            graph.setdefault(name, set())
            meta = station_meta.setdefault(name, {"name": name, "lines": set(), "lat": None, "lon": None})
            meta["lines"].add(line_name)
            if station.get("lat") and station.get("lon"):
                meta["lat"] = station["lat"]
                meta["lon"] = station["lon"]

        for i in range(len(names) - 1):
            a = names[i]
            b = names[i + 1]

            graph[a].add(b)
            graph[b].add(a)

    for a, b in TRANSFER_PAIRS:
        graph.setdefault(a, set())
        graph.setdefault(b, set())
        graph[a].add(b)
        graph[b].add(a)

    for meta in station_meta.values():
        meta["lines"] = sorted(meta["lines"])

    return graph, station_meta


def find_route(graph, start: str, goal: str):
    queue = deque([[start]])
    visited = set([start])

    while queue:
        path = queue.popleft()
        current = path[-1]

        if current == goal:
            return path

        for next_station in graph.get(current, []):
            if next_station not in visited:
                visited.add(next_station)
                queue.append(path + [next_station])

    return []


def resolve_station(raw_name: str, station_names: set):
    name = normalize_station_name(raw_name)
    if name in station_names:
        return name

    candidates = []
    for station in station_names:
        if name and (name in station or station in name):
            candidates.append(station)

    if not candidates:
        return None

    candidates.sort(key=lambda station: (len(station), station))
    return candidates[0]


def get_route(from_station: str, to_station: str):
    graph, station_meta = build_railway_graph()
    station_names = set(graph.keys())
    start = resolve_station(from_station, station_names)
    goal = resolve_station(to_station, station_names)

    if not start or not goal:
        return [], station_meta, {"from_station": start, "to_station": goal}

    route = find_route(graph, start, goal)
    print("経路:", " -> ".join(route))
    return route, station_meta, {"from_station": start, "to_station": goal}


def station_payload(name: str, station_meta: dict, index: int, total: int):
    meta = station_meta.get(name, {})
    return {
        "name": name,
        "lines": meta.get("lines", []),
        "lat": meta.get("lat"),
        "lon": meta.get("lon"),
        "position": round(index / max(total - 1, 1), 3),
    }


def stations_to_search(route: list[str]):
    if len(route) <= 8:
        return route

    selected = [route[0], route[-1]]
    middle_indexes = {
        len(route) // 4,
        len(route) // 2,
        (len(route) * 3) // 4,
    }
    for index in sorted(middle_indexes):
        selected.append(route[index])

    return list(dict.fromkeys(selected))


def search_cafes_for_route(route: list[str], purpose: str):
    cafes_by_station = []
    all_cafes = []

    for station in stations_to_search(route):
        cafes = search_hotpepper_cafes(station, purpose)
        cafes_by_station.append({
            "station": station,
            "cafes": cafes[:4],
        })
        all_cafes.extend(cafes[:3])

    return cafes_by_station, all_cafes

@app.post("/chat")
def chat(request: ChatRequest):
    user_message = request.message

    if any(word in user_message for word in ["リセット", "最初から", "やり直し"]):
        for key in conversation_slots:
            conversation_slots[key] = None
        return {
            "reply": "条件をリセットしました。出発駅、到着駅、利用目的、利用時刻を教えてください。",
            "slots": conversation_slots,
            "route": [],
            "cafesByStation": [],
        }

    prompt = f"""
あなたはタスク指向対話システムのNLUモジュールです。
以下のユーザー発話から、カフェ検索に必要な情報を抽出してください。

抽出する項目:
- from_station: 出発駅
- to_station: 到着駅
- purpose: カフェ利用目的（勉強、作業、休憩、デートなど）
- time: 利用予定時刻

必ずJSONのみを返してください。
不明な項目は null にしてください。

ユーザー発話:
{user_message}

出力例:
{{
  "from_station": "横浜",
  "to_station": "新宿",
  "purpose": "勉強",
  "time": null
}}
"""

    try:
        text = ask_openai(prompt, json_only=True)
        text = text.replace("```json", "").replace("```", "").strip()

        new_slots = json.loads(text)

        for key in conversation_slots:
            if new_slots.get(key):
                conversation_slots[key] = new_slots[key]

        slots = conversation_slots

        missing = []

        if not slots.get("from_station"):
            missing.append("出発駅")
        if not slots.get("to_station"):
            missing.append("到着駅")
        if not slots.get("purpose"):
            missing.append("利用目的")
        if not slots.get("time"):
            missing.append("利用時刻")

        if missing:
            reply = f"{'、'.join(missing)}を教えてください。"
        else:
            route, station_meta, resolved = get_route(
                slots["from_station"],
                slots["to_station"]
            )

            if not route:
                unknown = []
                if not resolved.get("from_station"):
                    unknown.append(slots["from_station"])
                if not resolved.get("to_station"):
                    unknown.append(slots["to_station"])

                unknown_text = f"（未対応: {', '.join(unknown)}）" if unknown else ""
                reply = (
                    f"{slots['from_station']}駅から{slots['to_station']}駅までの経路を取得できませんでした。{unknown_text}\n"
                    "現在は京王線・京王相模原線・京王井の頭線・小田急小田原線・小田急江ノ島線・小田急多摩線に対応しています。"
                )

                return {
                    "reply": reply,
                    "slots": slots,
                    "route": [],
                    "cafesByStation": [],
                }

            cafes_by_station, all_cafes = search_cafes_for_route(
                route,
                slots["purpose"]
            )

            if not all_cafes:
                reply = (
                    f"{resolved['from_station']}駅から{resolved['to_station']}駅への経路 "
                    f"（{' → '.join(route)}）上ではカフェ候補が見つかりませんでした。"
                )

                return {
                    "reply": reply,
                    "slots": slots,
                    "route": [
                        station_payload(station, station_meta, index, len(route))
                        for index, station in enumerate(route)
                    ],
                    "cafesByStation": cafes_by_station,
                }

            recommendation = generate_recommendation(
                "・".join([item["station"] for item in cafes_by_station if item["cafes"]][:5]),
                slots["purpose"],
                slots["time"],
                all_cafes
            )

            cafe_station_names = [item["station"] for item in cafes_by_station if item["cafes"]]
            reply = (
                f"{resolved['from_station']}駅から{resolved['to_station']}駅までの経路を見つけました。\n"
                f"経路: {' → '.join(route)}\n"
                f"カフェ候補があった駅: {', '.join(cafe_station_names)}\n\n"
                f"{recommendation}"
            )

        return {
            "reply": reply,
            "slots": slots,
            "route": [
                station_payload(station, station_meta, index, len(route))
                for index, station in enumerate(route)
            ] if "route" in locals() else [],
            "cafesByStation": cafes_by_station if "cafes_by_station" in locals() else [],
        }

    except Exception as e:
        print("ERROR:", e)
        return {
            "reply": f"API呼び出し中にエラーが発生しました。\n{str(e)}",
            "error": str(e),
        }
