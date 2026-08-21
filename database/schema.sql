PRAGMA foreign_keys = ON;


-- =========================================================
-- USUARIOS
-- =========================================================

CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,

    username TEXT NOT NULL COLLATE NOCASE UNIQUE,
    email TEXT NOT NULL COLLATE NOCASE UNIQUE,
    password_hash TEXT NOT NULL,
    display_name TEXT NOT NULL,

    role TEXT NOT NULL DEFAULT 'client'
        CHECK (role IN ('client', 'admin')),

    country_code TEXT NOT NULL DEFAULT 'ES'
        CHECK (length(country_code) = 2),

    profile_public INTEGER NOT NULL DEFAULT 0
        CHECK (profile_public IN (0, 1)),

    is_active INTEGER NOT NULL DEFAULT 1
        CHECK (is_active IN (0, 1)),

    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);


-- =========================================================
-- CONTENIDO AUDIOVISUAL
-- =========================================================

CREATE TABLE IF NOT EXISTS media (
    id INTEGER PRIMARY KEY AUTOINCREMENT,

    tmdb_id INTEGER,

    media_type TEXT NOT NULL
        CHECK (media_type IN ('movie', 'series')),

    title TEXT NOT NULL,
    original_title TEXT,
    overview TEXT,

    release_date TEXT,
    release_year INTEGER,

    runtime_minutes INTEGER
        CHECK (
            runtime_minutes IS NULL
            OR runtime_minutes > 0
        ),

    original_language TEXT,

    poster_path TEXT,
    backdrop_path TEXT,

    tmdb_rating REAL
        CHECK (
            tmdb_rating IS NULL
            OR tmdb_rating BETWEEN 0 AND 10
        ),

    tmdb_vote_count INTEGER
        CHECK (
            tmdb_vote_count IS NULL
            OR tmdb_vote_count >= 0
        ),

    popularity REAL,

    source TEXT NOT NULL DEFAULT 'manual'
        CHECK (source IN ('manual', 'tmdb')),

    is_visible INTEGER NOT NULL DEFAULT 1
        CHECK (is_visible IN (0, 1)),

    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    last_synced_at TEXT,

    UNIQUE (tmdb_id, media_type)
);


-- =========================================================
-- TEMPORADAS
-- =========================================================

CREATE TABLE IF NOT EXISTS seasons (
    id INTEGER PRIMARY KEY AUTOINCREMENT,

    tmdb_id INTEGER UNIQUE,

    media_id INTEGER NOT NULL,

    season_number INTEGER NOT NULL
        CHECK (season_number >= 0),

    name TEXT NOT NULL,
    overview TEXT,

    poster_path TEXT,
    air_date TEXT,

    episode_count INTEGER
        CHECK (
            episode_count IS NULL
            OR episode_count >= 0
        ),

    is_visible INTEGER NOT NULL DEFAULT 1
        CHECK (is_visible IN (0, 1)),

    FOREIGN KEY (media_id)
        REFERENCES media(id)
        ON UPDATE CASCADE
        ON DELETE CASCADE,

    UNIQUE (media_id, season_number)
);


-- =========================================================
-- EPISODIOS
-- =========================================================

CREATE TABLE IF NOT EXISTS episodes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,

    tmdb_id INTEGER UNIQUE,

    season_id INTEGER NOT NULL,

    episode_number INTEGER NOT NULL
        CHECK (episode_number > 0),

    name TEXT NOT NULL,
    overview TEXT,

    air_date TEXT,

    runtime_minutes INTEGER
        CHECK (
            runtime_minutes IS NULL
            OR runtime_minutes > 0
        ),

    still_path TEXT,

    is_visible INTEGER NOT NULL DEFAULT 1
        CHECK (is_visible IN (0, 1)),

    FOREIGN KEY (season_id)
        REFERENCES seasons(id)
        ON UPDATE CASCADE
        ON DELETE CASCADE,

    UNIQUE (season_id, episode_number)
);


-- =========================================================
-- GÉNEROS Y SUBGÉNEROS
-- =========================================================

CREATE TABLE IF NOT EXISTS genres (
    id INTEGER PRIMARY KEY AUTOINCREMENT,

    name TEXT NOT NULL COLLATE NOCASE UNIQUE,

    parent_id INTEGER,

    FOREIGN KEY (parent_id)
        REFERENCES genres(id)
        ON UPDATE CASCADE
        ON DELETE SET NULL,

    CHECK (
        parent_id IS NULL
        OR parent_id <> id
    )
);


CREATE TABLE IF NOT EXISTS media_genres (
    media_id INTEGER NOT NULL,
    genre_id INTEGER NOT NULL,

    PRIMARY KEY (media_id, genre_id),

    FOREIGN KEY (media_id)
        REFERENCES media(id)
        ON DELETE CASCADE,

    FOREIGN KEY (genre_id)
        REFERENCES genres(id)
        ON DELETE CASCADE
);


-- =========================================================
-- PAÍSES
-- =========================================================

CREATE TABLE IF NOT EXISTS countries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,

    iso_code TEXT NOT NULL UNIQUE
        CHECK (length(iso_code) = 2),

    name TEXT NOT NULL COLLATE NOCASE UNIQUE
);


CREATE TABLE IF NOT EXISTS media_countries (
    media_id INTEGER NOT NULL,
    country_id INTEGER NOT NULL,

    PRIMARY KEY (media_id, country_id),

    FOREIGN KEY (media_id)
        REFERENCES media(id)
        ON DELETE CASCADE,

    FOREIGN KEY (country_id)
        REFERENCES countries(id)
        ON DELETE CASCADE
);


-- =========================================================
-- ETIQUETAS
-- =========================================================

CREATE TABLE IF NOT EXISTS tags (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL COLLATE NOCASE UNIQUE
);


CREATE TABLE IF NOT EXISTS media_tags (
    media_id INTEGER NOT NULL,
    tag_id INTEGER NOT NULL,

    PRIMARY KEY (media_id, tag_id),

    FOREIGN KEY (media_id)
        REFERENCES media(id)
        ON DELETE CASCADE,

    FOREIGN KEY (tag_id)
        REFERENCES tags(id)
        ON DELETE CASCADE
);


-- =========================================================
-- FAVORITOS
-- =========================================================

CREATE TABLE IF NOT EXISTS favorites (
    user_id INTEGER NOT NULL,
    media_id INTEGER NOT NULL,

    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,

    PRIMARY KEY (user_id, media_id),

    FOREIGN KEY (user_id)
        REFERENCES users(id)
        ON DELETE CASCADE,

    FOREIGN KEY (media_id)
        REFERENCES media(id)
        ON DELETE CASCADE
);


-- =========================================================
-- PELÍCULAS VISTAS
-- =========================================================

CREATE TABLE IF NOT EXISTS movie_watches (
    user_id INTEGER NOT NULL,
    media_id INTEGER NOT NULL,

    watched_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,

    PRIMARY KEY (user_id, media_id),

    FOREIGN KEY (user_id)
        REFERENCES users(id)
        ON DELETE CASCADE,

    FOREIGN KEY (media_id)
        REFERENCES media(id)
        ON DELETE CASCADE
);


-- =========================================================
-- EPISODIOS VISTOS
-- =========================================================

CREATE TABLE IF NOT EXISTS episode_watches (
    user_id INTEGER NOT NULL,
    episode_id INTEGER NOT NULL,

    watched_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,

    PRIMARY KEY (user_id, episode_id),

    FOREIGN KEY (user_id)
        REFERENCES users(id)
        ON DELETE CASCADE,

    FOREIGN KEY (episode_id)
        REFERENCES episodes(id)
        ON DELETE CASCADE
);


-- =========================================================
-- VALORACIONES DE PELÍCULAS / SERIES
-- =========================================================

CREATE TABLE IF NOT EXISTS media_ratings (
    user_id INTEGER NOT NULL,
    media_id INTEGER NOT NULL,

    rating INTEGER NOT NULL
        CHECK (rating BETWEEN 1 AND 10),

    rated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,

    PRIMARY KEY (user_id, media_id),

    FOREIGN KEY (user_id)
        REFERENCES users(id)
        ON DELETE CASCADE,

    FOREIGN KEY (media_id)
        REFERENCES media(id)
        ON DELETE CASCADE
);


-- =========================================================
-- VALORACIONES DE TEMPORADAS
-- =========================================================

CREATE TABLE IF NOT EXISTS season_ratings (
    user_id INTEGER NOT NULL,
    season_id INTEGER NOT NULL,

    rating INTEGER NOT NULL
        CHECK (rating BETWEEN 1 AND 10),

    rated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,

    PRIMARY KEY (user_id, season_id),

    FOREIGN KEY (user_id)
        REFERENCES users(id)
        ON DELETE CASCADE,

    FOREIGN KEY (season_id)
        REFERENCES seasons(id)
        ON DELETE CASCADE
);


-- =========================================================
-- VALORACIONES DE EPISODIOS
-- =========================================================

CREATE TABLE IF NOT EXISTS episode_ratings (
    user_id INTEGER NOT NULL,
    episode_id INTEGER NOT NULL,

    rating INTEGER NOT NULL
        CHECK (rating BETWEEN 1 AND 10),

    rated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,

    PRIMARY KEY (user_id, episode_id),

    FOREIGN KEY (user_id)
        REFERENCES users(id)
        ON DELETE CASCADE,

    FOREIGN KEY (episode_id)
        REFERENCES episodes(id)
        ON DELETE CASCADE
);


-- =========================================================
-- ÍNDICES
-- =========================================================

CREATE INDEX IF NOT EXISTS idx_media_title
    ON media(title COLLATE NOCASE);

CREATE INDEX IF NOT EXISTS idx_media_type_visible
    ON media(media_type, is_visible);

CREATE INDEX IF NOT EXISTS idx_media_release_year
    ON media(release_year);

CREATE INDEX IF NOT EXISTS idx_seasons_media
    ON seasons(media_id);

CREATE INDEX IF NOT EXISTS idx_episodes_season
    ON episodes(season_id);

CREATE INDEX IF NOT EXISTS idx_media_genres_genre
    ON media_genres(genre_id);

CREATE INDEX IF NOT EXISTS idx_media_countries_country
    ON media_countries(country_id);

CREATE INDEX IF NOT EXISTS idx_media_tags_tag
    ON media_tags(tag_id);
CREATE INDEX IF NOT EXISTS idx_users_role_active
    ON users(role, is_active);

CREATE INDEX IF NOT EXISTS idx_favorites_media
    ON favorites(media_id);

CREATE INDEX IF NOT EXISTS idx_movie_watches_media
    ON movie_watches(media_id);

CREATE INDEX IF NOT EXISTS idx_episode_watches_episode
    ON episode_watches(episode_id);

CREATE INDEX IF NOT EXISTS idx_media_ratings_media
    ON media_ratings(media_id);

CREATE INDEX IF NOT EXISTS idx_season_ratings_season
    ON season_ratings(season_id);

CREATE INDEX IF NOT EXISTS idx_episode_ratings_episode
    ON episode_ratings(episode_id);