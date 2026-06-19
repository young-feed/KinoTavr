import os
import time
import requests
import psycopg2
from urllib.parse import quote  # Стандартный и безопасный импорт

DB_HOST = os.getenv("DB_HOST", "db")
DB_NAME = os.getenv("DB_NAME", "movies_db")
DB_USER = os.getenv("DB_USER", "user_admin")
DB_PASS = os.getenv("DB_PASSWORD", "super_secure_password")
KP_API_KEY = os.getenv("KP_API_KEY", "MD2BWNZ-3A64EXF-NN3E788-7XJGD5E")
KP_API_URL = "https://api.kinopoisk.dev/v1.4/movie"


def get_db_connection():
    return psycopg2.connect(host=DB_HOST, database=DB_NAME, user=DB_USER, password=DB_PASS)


def determine_movie_colors(genres: list, description: str = "") -> list:
    assigned_colors = []
    genres = [g.lower() for g in genres]
    desc = description.lower() if description else ""

    if any(g in genres for g in ["ужасы", "хоррор"]): assigned_colors.append("black")
    if any(g in genres for g in ["боевик", "криминал"]) and any(
        w in desc for w in ["месть", "убийство", "мафия", "банды"]): assigned_colors.append("crimson")
    if any(g in genres for g in ["драма", "мелодрама"]): assigned_colors.append("deep_blue")
    if any(g in genres for g in ["комедия", "семейный", "мультфильм"]): assigned_colors.append("yellow")
    if any(g in genres for g in ["фантастика", "фэнтези", "приключения"]): assigned_colors.append("purple")
    if any(g in genres for g in ["детектив", "триллер"]): assigned_colors.append("emerald")

    return list(set(assigned_colors)) if assigned_colors else ["emerald"]


def search_rutube_link(title: str, year: int) -> str:
    try:
        query = f"{title} {year} смотреть фильм"
        url = f"https://rutube.ru/api/search/video/?query={quote(query)}"

        # Увеличили таймаут до 10 секунд
        response = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)

        if response.status_code != 200:
            print(f"[!] Rutube вернул статус {response.status_code} для '{title}'.")
            return None

        results = response.json().get("results", [])
        for video in results:
            if video.get("duration", 0) > 2400:
                return video.get("video_url")
        if results:
            return results[0].get("video_url")

    except Exception as e:
        print(f"[-] Ошибка поиска Rutube для {title}: {e}")
    return None


def fetch_movies_from_kinopoisk(limit=50, page=1):
    print(f"[+] Скачиваем порцию фильмов с Кинопоиска: Страница {page}, Количество {limit}...")
    headers = {"accept": "application/json", "X-API-KEY": KP_API_KEY}
    params = {
        "page": page, "limit": limit,
        "selectFields": ["id", "name", "year", "description", "poster", "genres"],
        "type": "movie", "rating.kp": "7-10", "votes.kp": "10000-10000000"
    }

    try:
        response = requests.get(KP_API_URL, headers=headers, params=params, timeout=10)
        if response.status_code == 200:
            return response.json().get("docs", [])
        else:
            print(f"[-] Ошибка API Кинопоиска ({response.status_code}): {response.text}")
    except Exception as e:
        print(f"[-] Не удалось связаться с API Кинопоиска: {e}")
    return []


def save_to_database(conn, movie_data):
    cursor = conn.cursor()
    kp_id = movie_data.get("id")
    title = movie_data.get("name")
    year = movie_data.get("year")
    desc = movie_data.get("description", "")
    poster_data = movie_data.get("poster")
    poster_url = poster_data.get("url") if poster_data else None

    if not title or not kp_id: return

    kp_url = f"https://www.kinopoisk.ru/film/{kp_id}/"
    rutube_url = search_rutube_link(title, year)

    try:
        cursor.execute("""
            INSERT INTO movies (kinopoisk_id, title, year, description, poster_url, kp_url, rutube_url)
            VALUES (%s, %s, %s, %s, %s, %s, %s) 
            ON CONFLICT (kinopoisk_id) DO UPDATE SET rutube_url = EXCLUDED.rutube_url 
            RETURNING id;
        """, (kp_id, title, year, desc, poster_url, kp_url, rutube_url))

        movie_id = cursor.fetchone()[0]

        # Защита от "null" в жанрах
        genres_data = movie_data.get("genres") or []
        genres_list = [g["name"] for g in genres_data if "name" in g]
        colors = determine_movie_colors(genres_list, desc)

        for c in colors:
            cursor.execute("SELECT id FROM colors WHERE color_name = %s;", (c,))
            c_res = cursor.fetchone()
            if c_res:
                cursor.execute("""
                    INSERT INTO movie_colors (movie_id, color_id) 
                    VALUES (%s, %s) ON CONFLICT DO NOTHING;
                """, (movie_id, c_res[0]))

        conn.commit()
        print(f"[🟢] Успешно добавлен: '{title}' ({year}) -> Цвета: {colors}")
    except Exception as e:
        conn.rollback()
        print(f"[🔴] Ошибка сохранения '{title}': {e}")
    finally:
        cursor.close()


def main():
    print("[*] Парсер проекта KinoTavr запущен.")
    all_movies = []

    for page in [1, 2]:
        try:
            movies_batch = fetch_movies_from_kinopoisk(limit=50, page=page)
            if movies_batch: all_movies.extend(movies_batch)
            time.sleep(2)
        except Exception as e:
            print(f"[🔴] Ошибка скачивания страницы {page}: {e}")

    if not all_movies:
        print("[-] Не удалось получить фильмы. Завершение.")
        return

    print(f"[+] Получено {len(all_movies)} фильмов.")

    try:
        conn = get_db_connection()
    except Exception as e:
        print(f"[🔴] Ошибка БД: {e}")
        return

    for index, movie in enumerate(all_movies, start=1):
        try:
            save_to_database(conn, movie)
        except Exception as e:
            print(f"[🔴] Критическая ошибка фильма №{index}: {e}")
        time.sleep(1.5)

    conn.close()
    print(f"[+] Скрипт завершил работу.")


if __name__ == "__main__":
    main()