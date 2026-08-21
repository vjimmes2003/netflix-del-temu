from pathlib import Path
import sys

from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parents[1]

sys.path.insert(
    0,
    str(PROJECT_ROOT),
)

load_dotenv(
    PROJECT_ROOT / ".env"
)

from app.tmdb_client import TMDBClient


def main():
    print("=== PRUEBA DE CONEXIÓN CON TMDB ===\n")

    client = TMDBClient()

    movie = client.movie_details(157336)

    print("[OK] Conexión realizada")
    print(f"TMDB ID: {movie['id']}")
    print(f"Título: {movie['title']}")
    print(f"Título original: {movie['original_title']}")
    print(f"Fecha: {movie.get('release_date')}")
    print(f"Duración: {movie.get('runtime')} minutos")

    poster = client.image_url(
        movie.get("poster_path")
    )

    print(f"Poster disponible: {'Sí' if poster else 'No'}")
    
    series = client.series_details(1396)

    print("\n=== PRUEBA DE SERIE ===")
    print(f"TMDB ID: {series['id']}")
    print(f"Título: {series['name']}")
    print(f"Temporadas: {series['number_of_seasons']}")
    print(f"Episodios: {series['number_of_episodes']}")

    poster = client.image_url(
        series.get("poster_path")
    )

    print(f"Poster disponible: {'Sí' if poster else 'No'}")

if __name__ == "__main__":
    main()