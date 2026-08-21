# Modelo entidad-relación

El modelo se divide visualmente en tres bloques: **usuarios y actividad**, **catálogo audiovisual** y **clasificación**. Las tablas intermedias representan relaciones N:M.

```mermaid
flowchart LR

    subgraph U["Usuarios y actividad"]
        USERS[USERS]

        FAVORITES[FAVORITES]
        MOVIE_WATCHES[MOVIE_WATCHES]
        EPISODE_WATCHES[EPISODE_WATCHES]

        MEDIA_RATINGS[MEDIA_RATINGS]
        SEASON_RATINGS[SEASON_RATINGS]
        EPISODE_RATINGS[EPISODE_RATINGS]

        USERS --> FAVORITES
        USERS --> MOVIE_WATCHES
        USERS --> EPISODE_WATCHES
        USERS --> MEDIA_RATINGS
        USERS --> SEASON_RATINGS
        USERS --> EPISODE_RATINGS
    end

    subgraph C["Catálogo audiovisual"]
        MEDIA[MEDIA]
        SEASONS[SEASONS]
        EPISODES[EPISODES]

        MEDIA -->|1:N| SEASONS
        SEASONS -->|1:N| EPISODES
    end

    subgraph K["Clasificación"]
        GENRES[GENRES]
        COUNTRIES[COUNTRIES]
        TAGS[TAGS]

        MEDIA_GENRES[MEDIA_GENRES]
        MEDIA_COUNTRIES[MEDIA_COUNTRIES]
        MEDIA_TAGS[MEDIA_TAGS]

        GENRES --> MEDIA_GENRES
        COUNTRIES --> MEDIA_COUNTRIES
        TAGS --> MEDIA_TAGS

        GENRES -->|subgéneros| GENRES
    end

    FAVORITES --> MEDIA
    MOVIE_WATCHES --> MEDIA
    MEDIA_RATINGS --> MEDIA

    EPISODE_WATCHES --> EPISODES
    SEASON_RATINGS --> SEASONS
    EPISODE_RATINGS --> EPISODES

    MEDIA --> MEDIA_GENRES
    MEDIA --> MEDIA_COUNTRIES
    MEDIA --> MEDIA_TAGS
```

## Relaciones principales

- `USERS` y `MEDIA` se relacionan N:M mediante `FAVORITES`, `MOVIE_WATCHES` y `MEDIA_RATINGS`.
- Las series se estructuran como `MEDIA → SEASONS → EPISODES`.
- El seguimiento de episodios se registra en `EPISODE_WATCHES`.
- Las valoraciones pueden realizarse sobre contenido, temporadas y episodios.
- Géneros, países y etiquetas se relacionan con `MEDIA` mediante tablas intermedias.
- `GENRES` utiliza una relación autorreferenciada para permitir subgéneros.
