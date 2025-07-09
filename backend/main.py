import os
import redis
import json
from fastapi import FastAPI, HTTPException, Query
import requests
from bs4 import BeautifulSoup
import uvicorn

# FastAPIアプリケーションのインスタンスを作成
app = FastAPI(
    title="CampusPal API",
    description="東京都市大学のシラバス情報を取得するためのAPIです。",
    version="1.6.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json"
)

# --- Redisへの接続設定 ---
# 環境変数からRedisのURLを取得。なければデフォルト値を使用。
REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379")
try:
    # Redisクライアントを作成。レスポンスは自動でデコードする。
    redis_client = redis.from_url(REDIS_URL, decode_responses=True)
    # 接続テスト
    redis_client.ping()
    print("Redisに正常に接続しました。")
except redis.exceptions.ConnectionError as e:
    print(f"Redisへの接続に失敗しました: {e}")
    redis_client = None # 接続失敗時はNoneに設定
# ---

# シラバス検索のベースURL
BASE_URL = "https://websrv.tcu.ac.jp/tcu_web_v3/slbssbdr.do"

# ★ 修正箇所: LABEL_TO_KEY_MAP から "分野系列" を削除
LABEL_TO_KEY_MAP = {
    "授業科目名": "course_name",
    "単位数": "credits",
    "開講年度": "academic_year",
    "学年": "student_year",
    "学期": "term",
    "担当者": "instructors",
}

def get_syllabus_data(kougicd: str, rishunen: str):
    """
    指定されたパラメータでシラバスサイトをスクレイピングし、基本情報を抽出する。
    """
    params = {
        "value(risyunen)": rishunen,
        "value(semekikn)": "1",
        "value(kougicd)": kougicd,
    }
    try:
        response = requests.get(BASE_URL, params=params, timeout=10)
        response.raise_for_status()
        response.encoding = response.apparent_encoding
        soup = BeautifulSoup(response.text, 'html.parser')
        
        tables = soup.find_all('table', class_='syllabus_detail')
        if not tables:
            raise ValueError("シラバスのデータテーブルが見つかりません。")

        data = {}
        for table in tables:
            rows = table.find_all('tr')
            for row in rows:
                label_cell = row.find('td', class_='label_kougi')
                if not label_cell:
                    continue
                
                label_text = label_cell.get_text(separator="|").split("|")[0].strip()

                if label_text in LABEL_TO_KEY_MAP:
                    key = LABEL_TO_KEY_MAP[label_text]
                    value_cell = row.find('td', class_='kougi')
                    if value_cell:
                        if key == "instructors":
                            p_tags = value_cell.find_all('p')
                            data[key] = [p.get_text(strip=True).replace('　', ' ') for p in p_tags if p.get_text(strip=True)]
                        elif key in ["credits", "academic_year"]:
                            value = value_cell.get_text(strip=True)
                            try:
                                data[key] = int(value)
                            except (ValueError, TypeError):
                                data[key] = value
                        else:
                            data[key] = value_cell.get_text(strip=True)
        return data
    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=504, detail=f"シラバスサイトへのアクセスに失敗しました: {e}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"データの解析中に予期せぬエラーが発生しました: {e}")

@app.get("/api/syllabus/{kougicd}", summary="シラバス情報取得")
def read_syllabus(
    kougicd: str,
    rishunen: str = Query(..., description="履修年度 (例: 2024)", regex="^[0-9]{4}$")
):
    """
    講義コードと履修年度に基づいてシラバス情報を取得します。
    データはRedisに無期限でキャッシュされます。
    """
    if not redis_client:
        syllabus_info = get_syllabus_data(kougicd, rishunen)
        if not syllabus_info:
            raise HTTPException(status_code=404, detail="指定された条件の情報が見つかりませんでした。")
        return syllabus_info

    cache_key = f"syllabus:{rishunen}:{kougicd}"

    try:
        cached_data = redis_client.get(cache_key)
        if cached_data:
            print(f"Cache HIT: {cache_key}")
            return json.loads(cached_data)

        print(f"Cache MISS: {cache_key}")
        syllabus_info = get_syllabus_data(kougicd, rishunen)
        if not syllabus_info:
            raise HTTPException(status_code=404, detail="指定された条件の情報が見つかりませんでした。")

        redis_client.set(cache_key, json.dumps(syllabus_info, ensure_ascii=False))

        return syllabus_info

    except redis.exceptions.RedisError as e:
        print(f"Redis Error: {e}")
        syllabus_info = get_syllabus_data(kougicd, rishunen)
        if not syllabus_info:
            raise HTTPException(status_code=404, detail="指定された条件の情報が見つかりませんでした。")
        return syllabus_info

# uvicornでサーバーを起動するための設定
if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
