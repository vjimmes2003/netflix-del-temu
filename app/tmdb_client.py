import os

import requests


class TMDBClient:
    """Cliente sencillo para consultar la API de TMDB."""

    BASE_URL = "https://api.themoviedb.org/3"
    IMAGE_BASE_URL = "https://image.tmdb.org/t/p"

    def __init__(self, token=None, language="es-ES"):
        self.token = token or os.getenv("TMDB_TOKEN")
        self.language = language

        if not self.token:
            raise ValueError(
                "No se ha configurado TMDB_TOKEN en el archivo .env."
            )

        self.session = requests.Session()

        self.session.headers.update(
            {
                "Authorization": f"Bearer {self.token}",
                "Accept": "application/json",
            }
        )

    def _get(self, endpoint, params=None):
        """Realiza una petición GET a TMDB."""

        request_params = {
            "language": self.language,
        }

        if params:
            request_params.update(params)

        response = self.session.get(
            f"{self.BASE_URL}{endpoint}",
            params=request_params,
            timeout=15,
        )

        response.raise_for_status()

        return response.json()

    def movie_details(self, tmdb_id):
        """Obtiene los datos completos de una película."""

        return self._get(
            f"/movie/{tmdb_id}",
            {
                "append_to_response": "keywords",
            },
        )

    def series_details(self, tmdb_id):
        """Obtiene los datos completos de una serie."""

        return self._get(
            f"/tv/{tmdb_id}",
            {
                "append_to_response": "keywords",
            },
        )

    def season_details(self, series_id, season_number):
        """Obtiene temporadas y episodios de una serie."""

        return self._get(
            f"/tv/{series_id}/season/{season_number}"
        )

    def discover_movies(self, page=1):
        """Obtiene películas ordenadas por popularidad."""

        return self._get(
            "/discover/movie",
            {
                "page": page,
                "include_adult": "false",
                "sort_by": "popularity.desc",
            },
        )

    def discover_series(self, page=1):
        """Obtiene series ordenadas por popularidad."""

        return self._get(
            "/discover/tv",
            {
                "page": page,
                "include_adult": "false",
                "sort_by": "popularity.desc",
            },
        )

    @classmethod
    def image_url(cls, path, size="w500"):
        """Construye la URL completa de una imagen de TMDB."""

        if not path:
            return None

        return f"{cls.IMAGE_BASE_URL}/{size}{path}"