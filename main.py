import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
import json
import httpx  # Используем для прямых асинхронных запросов к API Gemini
from dotenv import load_dotenv
import psycopg2
from psycopg2.extras import RealDictCursor

load_dotenv()

class Message(BaseModel):
    question: str
    answer: str

class BotRequest(BaseModel):
    user_id: int
    consversion: list[Message]

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def get_db_connection():
    return psycopg2.connect(
        host=os.getenv("DB_HOST", "localhost"),
        database=os.getenv("DB_NAME", "movies_db"),
        user=os.getenv("DB_USER", "user_admin"),
        password=os.getenv("DB_PASSWORD", "super_secure_password"),
        port=os.getenv("DB_PORT", "5432"),
        cursor_factory=RealDictCursor
    )

SYSTEM_PROMPT = """
Ты — Кинотавр, эмпатичный, харизматичный кинокритик и бот-психолог.

ТВОЯ ЦЕЛЬ:
- Считать настроение пользователя.
- Если клиент сомневается или не знает чего хочет — креативно разговорить его.
- Точно определить цвет настроения из Палитры и передать команду системе.

🔥 ГЛАВНОЕ (КРИТИЧЕСКИ ВАЖНО):
Ты НЕ ищешь и НЕ предлагаешь конкретные названия фильмов! Твоя задача — только определить эмоцию и выдать её цвет. Фильм подберет база данных.
ТВОЙ ОТВЕТ ДОЛЖЕН БЫТЬ СТРОГО В ФОРМАТЕ JSON.

🚨 ФОРМАТ ОТВЕТА (выбирай один из двух):
{"action": "ask", "text": "Сгенерируй здесь свой уникальный, живой и короткий вопрос."}
ИЛИ
{"action": "recommend", "text": "Сгенерируй здесь свою стильную подводку (1-2 предложения).", "color": "выбранный_цвет_из_палитры"}

🎨 ПАЛИТРА НАСТРОЕНИЙ (СТРОГИЕ КЛЮЧИ):
- "deep_blue" — Грусть (Меланхолия, драмы, одиночество, хочется поплакать).
- "yellow" — Радость (Комедии, семейные, позитив, легкое кино на вечер).
- "crimson" — Жестокость (Криминал, жесткий экшен, месть, драйв).
- "black" — Страх (Ужасы, хорроры, саспенс, гнетущая атмосфера).
- "purple" — Загадочность (Фантастика, космос, магия, фэнтези, сказки).
- "emerald" — Интрига (Детективы, шпионские игры, заговоры, головоломки).
"""

@app.get("/ping")
async def ping_server():
    return {"status": "Kinotavr is alive!"}

@app.post('/chat')
async def process_chat(request: BotRequest):
    # Формируем историю диалога для Gemini API
    contents = []
    for msg in request.consversion:
        contents.append({"role": "model", "parts": [{"text": msg.question}]})
        contents.append({"role": "user", "parts": [{"text": msg.answer}]})
        
    if not contents:
        contents.append({"role": "user", "parts": [{"text": "Привет! Начнем диалог."}]})

    # Формируем Payload по официальной спецификации Google Gemini API
    gemini_payload = {
        "contents": contents,
        "systemInstruction": {
            "parts": [{"text": SYSTEM_PROMPT}]
        },
        "generationConfig": {
            "responseMimeType": "application/json",
            "temperature": 0.7
        }
    }

    api_key = os.getenv("GEMINI_API_KEY")
    # Новый корректный URL согласно официальным докам Google AI
    url = f"https://api-gateway.ai.google.dev/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(url, json=gemini_payload, timeout=15.0)
            
            if response.status_code != 200:
                return {"action": "ask", "text": f"Ошибка Gemini API ({response.status_code}): {response.text}"}
                
            response_data = response.json()
            ai_answer_text = response_data['candidates'][0]['content']['parts'][0]['text']
            
    except Exception as e:
        return {"action": "ask", "text": f"Не удалось связаться с ИИ: {str(e)}"}

    # Превращаем ответ ИИ в Python-словарь
    try:
        result = json.loads(ai_answer_text)
    except (json.JSONDecodeError, KeyError):
        return {"action": "ask", "text": "Не совсем понял, давай уточним. Какое настроение ищем?"}

    # Если AI определил цвет настроения, достаем фильм из базы
    if result.get("action") == "recommend" and result.get("color"):
        try:
            conn = get_db_connection()
            cursor = conn.cursor()

            query = """
                     SELECT m.* FROM movies m
                     JOIN movie_colors mc ON m.id = mc.movie_id
                     JOIN colors c ON mc.color_id = c.id
                     WHERE c.color_name = %s
                     ORDER BY RANDOM()
                     LIMIT 1;
                 """
            cursor.execute(query, (result["color"],))
            movie = cursor.fetchone()
            cursor.close()
            conn.close()

            if movie:
                result["movie"] = dict(movie)
            else:
                result["movie"] = None
        except Exception as e:
            result["movie"] = None
            result["db_error"] = str(e)

    return result

@app.get('/colors')
async def get_colors():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id, color_name, hex_code, mood_description FROM colors;")
        colors = cursor.fetchall()
        cursor.close()
        conn.close()
        return {"colors": [dict(c) for c in colors]}
    except Exception as e:
        return {"error": str(e)}