-- Таблица фильмов
CREATE TABLE IF NOT EXISTS movies (
    id SERIAL PRIMARY KEY,
    kinopoisk_id INT UNIQUE,
    title VARCHAR(255) NOT NULL,
    year INT,
    description TEXT,                  -- TEXT вместо VARCHAR для длинных описаний
    poster_url VARCHAR(512),
    kp_url VARCHAR(512),
    rutube_url VARCHAR(512),
    created_at TIMESTAMP DEFAULT NOW()
);

-- Таблица цветов (настроений)
CREATE TABLE IF NOT EXISTS colors (
    id SERIAL PRIMARY KEY,
    color_name VARCHAR(50) UNIQUE NOT NULL,
    hex_code VARCHAR(7),
    mood_description VARCHAR(255)
);

-- Таблица связей Многие-ко-Многим
CREATE TABLE IF NOT EXISTS movie_colors (
    movie_id INT REFERENCES movies(id) ON DELETE CASCADE,
    color_id INT REFERENCES colors(id) ON DELETE CASCADE,
    weight INT DEFAULT 100,
    PRIMARY KEY (movie_id, color_id)
);

-- Таблица действий пользователей (СЮДА БУДУТ ПАДАТЬ ЛАЙКИ/ДИЗЛАЙКИ)
CREATE TABLE IF NOT EXISTS user_actions (
    id SERIAL PRIMARY KEY,
    telegram_user_id BIGINT NOT NULL,        -- BIGINT для длинных ID телеграма
    movie_id INT REFERENCES movies(id) ON DELETE CASCADE,
    action_type VARCHAR(20) NOT NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(telegram_user_id, movie_id, action_type)
);

-- Индексы для ускорения выборок
CREATE INDEX IF NOT EXISTS idx_movies_kinopoisk_id ON movies(kinopoisk_id);
CREATE INDEX IF NOT EXISTS idx_movie_colors_color ON movie_colors(color_id);
CREATE INDEX IF NOT EXISTS idx_user_actions_tg_user ON user_actions(telegram_user_id);

-- Наполнение расширенной палитры
INSERT INTO colors (color_name, hex_code, mood_description) VALUES
('deep_blue',   '#1A365D', 'Грусть (Меланхолия, драмы, одиночество)'),
('yellow',      '#ECC94B', 'Радость (Комедии, семейные, позитив)'),
('crimson',     '#9B2C2C', 'Жестокость (Криминал, жесткий экшен, месть)'),
('black',       '#171717', 'Страх (Ужасы, хорроры, гнетущая атмосфера)'),
('purple',      '#553C9A', 'Загадочность (Фантастика, космос, магия, фэнтези)'),
('emerald',     '#22543D', 'Интрига (Детективы, шпионские игры, заговоры)')
ON CONFLICT (color_name) DO NOTHING;