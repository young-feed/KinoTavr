import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
import json
import asyncio
# Импортируем официальную библиотеку Google AI
import google.generativeai as genai
from dotenv import load_dotenv
import psycopg2
from psycopg2.extras import RealDictCursor

load_dotenv()

# Настраиваем Gemini API
genai.configure(api_key=os.getenv("OPENAI_API_KEY"))

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

Вариант 1 (Настроение непонятно, нужно уточнить):
{"action": "ask", "text": "Сгенерируй здесь свой уникальный, живой и короткий вопрос."}

Вариант 2 (Настроение понятно, делаем рекомендацию):
{"action": "recommend", "text": "Сгенерируй здесь свою стильную подводку (1-2 предложения).", "color": "выбранный_цвет_из_палитры"}

🎨 ПАЛИТРА НАСТРОЕНИЙ (СТРОГИЕ КЛЮЧИ):
- "deep_blue" — Грусть (Меланхолия, драмы, одиночество, хочется поплакать).
- "yellow" — Радость (Комедии, семейные, позитив, легкое кино на вечер).
- "crimson" — Жестокость (Криминал, жесткий экшен, месть, драйв).
- "black" — Страх (Ужасы, хорроры, саспенс, гнетущая атмосфера).
- "purple" — Загадочность (Фантастика, космос, магия, фэнтези, сказки).
- "emerald" — Интрига (Детективы, шпионские игры, заговоры, головоломки).

🧠 КАК ВЕСТИ ДИАЛОГ:
1. ЕСЛИ КЛИЕНТ ГОВОРИТ "НЕ ЗНАЮ" ИЛИ "ЛЮБОЙ":
- Не задавай скучные вопросы вроде "Какой жанр предпочитаешь?".
- Предлагай ассоциации или микро-игры в поле text. Например: "Представь, что за окном дождь. Нальем горячий чай и включим что-то уютное, или добавим мрачного детектива?", "Выбирай: полет в космос, разборки мафии или магия?", "Хочешь, чтобы фильм обнял тебя или дал пинка?".

2. ЕСЛИ НАСТРОЕНИЕ ЯСНО:
- Сразу возвращай action: recommend. 
- В поле text пиши уверенную подводку, например: "То что нужно. Заваривай чай, я нашел идеальный вариант.", "Окей, хочется крови и зрелищ. Держи пушку."

🧹 АНТИ-ПОВТОРЫ И ЗАПРЕТЫ:
- НИКОГДА не копируй мои инструкции в свой ответ. Придумывай текст сам.
- НИКОГДА не упоминай названия фильмов, актеров или режиссеров.
- НИКОГДА не пиши "Я понял, что тебе грустно". Действуй тоньше.
- Общайся на "ты", будь уверенным киноманом-психологом, а не роботом-помощником.
"""

@app.get("/ping")
async def ping_server():
    return {"status": "Kinotavr is alive!"}

@app.post('/chat')
async def process_chat(request: BotRequest):
    # Создаем историю диалога в формате, который понимает Gemini
    contents = []
    
    for msg in request.consversion:
        # У Лламы ты пушил раздельно, в Gemini мы группируем реплики
        contents.append({"role": "model", "parts": [{"text": msg.question}]})
        contents.append({"role": "user", "parts": [{"text": msg.answer}]})

    # Используем модель gemini-1.5-flash — она очень быстрая и бесплатная
    model = genai.GenerativeModel(
        model_name="gemini-1.5-flash",
        system_instruction=SYSTEM_PROMPT, # Системный промпт вшивается сюда
        generation_config={
            "response_mime_type": "application/json", # Жестко требуем JSON на выходе
            "temperature": 0.7
        }
    )

    try:
        # Библиотека google-generativeai не имеет нативного async метода, 
        # поэтому мы безопасно запускаем синхронный вызов в асинхронном потоке (ThreadPool)
        loop = asyncio.get_running_loop()
        response = await loop.run_in_executor(
            None, 
            lambda: model.generate_content(contents if contents else "Привет! Начнем диалог.")
        )
        ai_answer_text = response.text
    except Exception as e:
        # Если само API Google упало (например, проблемы с ключом)
        return {"action": "ask", "text": f"Проблема с ИИ-центром: {str(e)}"}

    # Превращаем ответ в Python-словарь
    try:
        result = json.loads(ai_answer_text)
    except json.JSONDecodeError:
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