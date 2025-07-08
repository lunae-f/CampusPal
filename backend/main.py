import os
import redis # 追加
import json # 追加
from fastapi import FastAPI, HTTPException, Query
import requests
from bs4 import BeautifulSoup
import uvicorn

app = FastAPI(docs_url="/api/docs", redoc_url="/api/redoc", openapi_url="/api/openapi.json")

# --- Redisへの接続設定 ---
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")
redis_client = redis.from_url(REDIS_URL, decode_responses=True)
# ---

BASE_URL = "https://websrv.tcu.ac.jp/tcu_web_v3/slbssbdr.do"

LABEL_TO_KEY_MAP = {
    "授業科目名": "course_name", "単位数": "credits", "開講年度": "academic_year",
    "開講学科": "department", "分野系列": "category", "学年": "student_year",
    "学期": "term", "担当者": "instructors",
}

def get_syllabus_data(kougicd: str, rishunen: str, crclumcd: str):
    params = {
        "value(risyunen)": rishunen, "value(semekikn)": "1",
        "value(kougicd)": kougicd, "value(crclumcd)": crclumcd,
    }
    try:
        response = requests.get(BASE_URL, params=params)
        response.raise_for_status()
        response.encoding = response.apparent_encoding
        soup = BeautifulSoup(response.text, 'html.parser')
        tables = soup.find_all('table', class_='syllabus_detail')
        if not tables: raise ValueError("シラバスのデータテーブルが見つかりません。")
        data = {}
        for table in tables:
            rows = table.find_all('tr')
            for row in rows:
                label_cell = row.find('td', class_='label_kougi')
                if not label_cell: continue
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
                            try: data[key] = int(value)
                            except (ValueError, TypeError): data[key] = value
                        elif key == "category":
                            data[key] = value_cell.get_text(strip=True).replace('■', '')
                        else:
                            data[key] = value_cell.get_text(strip=True)
        return data
    except requests.exceptions.RequestException as e: raise HTTPException(status_code=504, detail=f"シラバスサイトへのアクセスに失敗しました: {e}")
    except Exception as e: raise HTTPException(status_code=500, detail=f"予期せぬエラーが発生しました: {e}")


@app.get("/api/syllabus/{kougicd}")
def read_syllabus(kougicd: str, rishunen: str = Query(..., description="履修年度 (例: 2024)"), crclumcd: str = Query(..., description="カリキュラムコード (例: s24160)")):
    # --- ここからロジックを修正 ---

    # 1. キャッシュ用のキーを作成
    cache_key = f"syllabus:{rishunen}:{kougicd}:{crclumcd}"

    try:
        # 2. Redisキャッシュを確認
        cached_data = redis_client.get(cache_key)
        if cached_data:
            # キャッシュがあれば、それをJSONとして返却
            return json.loads(cached_data)

        # 3. キャッシュがなければ、スクレイピングを実行
        syllabus_info = get_syllabus_data(kougicd, rishunen, crclumcd)
        if not syllabus_info: 
            raise HTTPException(status_code=404, detail="指定された条件の情報が見つかりませんでした。")
        
        # 4. 取得した情報をRedisに保存 (有効期限を1日に設定)
        redis_client.setex(cache_key, 86400, json.dumps(syllabus_info, ensure_ascii=False))

        return syllabus_info
    
    except redis.exceptions.RedisError as e:
        # Redisに接続できない場合は、キャッシュを使わずに直接スクレイピングする
        print(f"Redis Error: {e}")
        syllabus_info = get_syllabus_data(kougicd, rishunen, crclumcd)
        if not syllabus_info: 
            raise HTTPException(status_code=404, detail="指定された条件の情報が見つかりませんでした。")
        return syllabus_info