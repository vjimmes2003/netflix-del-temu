import unicodedata


# Contenido que nunca se mostrará en el catálogo de clientes.
EXPLICIT_KEYWORDS = {
    "hentai",
    "pornography",
    "pornographic",
    "hardcore",
    "softcore",
    "explicit sex",
    "unsimulated sex",
    "porn industry",
    "erotic animation",
    "erotic anime",
}

EXPLICIT_CERTIFICATIONS = {
    "X",
    "XXX",
}


# Contenido permitido, pero oculto por defecto hasta que el usuario
# active expresamente la visualización de contenido maduro.
MATURE_KEYWORDS = {
    "ecchi",
    "sexual humor",
    "sex comedy",
    "nudity",
    "eroticism",
}

MATURE_CERTIFICATIONS = {
    "18",
    "18+",
    "NC-17",
    "TV-MA",
}


def extract_keywords(data, media_type):
    """Obtiene las palabras clave incluidas en la respuesta de TMDB."""

    keyword_data = data.get("keywords") or {}

    if media_type == "movie":
        return keyword_data.get("keywords", [])

    return keyword_data.get("results", [])


def keyword_names(data, media_type):
    """Normaliza las palabras clave para facilitar su comparación."""

    return {
        keyword.get("name", "").strip().casefold()
        for keyword in extract_keywords(data, media_type)
        if keyword.get("name")
    }


def find_matching_keyword(names, configured_keywords):
    """Devuelve la primera palabra clave que coincide con la política."""

    for name in names:
        for configured in configured_keywords:
            if configured in name:
                return name

    return None


def get_movie_certification(data, preferred_country="ES"):
    """Obtiene la certificación de una película priorizando España."""

    release_data = data.get("release_dates") or {}
    results = release_data.get("results", [])

    for country in (preferred_country, "US"):
        country_data = next(
            (
                result
                for result in results
                if result.get("iso_3166_1") == country
            ),
            None,
        )

        if not country_data:
            continue

        certifications = [
            release.get("certification", "").strip()
            for release in country_data.get("release_dates", [])
            if release.get("certification", "").strip()
        ]

        if certifications:
            return certifications[-1], country

    return None, None


def get_series_certification(data, preferred_country="ES"):
    """Obtiene la clasificación de una serie priorizando España."""

    rating_data = data.get("content_ratings") or {}
    results = rating_data.get("results", [])

    for country in (preferred_country, "US"):
        result = next(
            (
                item
                for item in results
                if item.get("iso_3166_1") == country
            ),
            None,
        )

        if not result:
            continue

        rating = (result.get("rating") or "").strip()

        if rating:
            return rating, country

    return None, None


def get_certification(data, media_type):
    """Obtiene la certificación según el tipo de contenido."""

    if media_type == "movie":
        return get_movie_certification(data)

    return get_series_certification(data)


def classify_content(data, media_type):
    """
    Clasifica un contenido como general, mature o explicit.

    La clasificación 16 y la clasificación R se conservan como metadatos,
    pero no se consideran motivo suficiente para ocultar el contenido.

    Tampoco se considera "adult animation" como contenido maduro por sí solo,
    ya que describe el público objetivo y no implica contenido sexual explícito.

    Devuelve:
        content_level,
        content_reason,
        certification,
        certification_country
    """

    certification, country = get_certification(
        data,
        media_type,
    )

    normalized_certification = (
        certification.strip().upper()
        if certification
        else None
    )

    names = keyword_names(
        data,
        media_type,
    )

    # Nivel explícito: nunca visible para clientes.
    if data.get("adult") is True:
        return (
            "explicit",
            "Marcado como adult por TMDB",
            certification,
            country,
        )

    explicit_keyword = find_matching_keyword(
        names,
        EXPLICIT_KEYWORDS,
    )

    if explicit_keyword:
        return (
            "explicit",
            f"Keyword: {explicit_keyword}",
            certification,
            country,
        )

    if (
        normalized_certification
        and normalized_certification
        in EXPLICIT_CERTIFICATIONS
    ):
        return (
            "explicit",
            f"Certificación: {certification}",
            certification,
            country,
        )

    # Nivel maduro: visible únicamente si el usuario lo activa.
    mature_keyword = find_matching_keyword(
        names,
        MATURE_KEYWORDS,
    )

    if mature_keyword:
        return (
            "mature",
            f"Keyword: {mature_keyword}",
            certification,
            country,
        )

    if (
        normalized_certification
        and normalized_certification
        in MATURE_CERTIFICATIONS
    ):
        return (
            "mature",
            f"Certificación: {certification}",
            certification,
            country,
        )

    return (
        "general",
        None,
        certification,
        country,
    )


def has_latin_letters(text):
    """Comprueba si un título contiene caracteres del alfabeto latino."""

    if not text:
        return False

    for character in text:
        if not character.isalpha():
            continue

        if "LATIN" in unicodedata.name(character, ""):
            return True

    return False


def apply_title_fallback(client, data, media_type):
    """
    Prioriza el título español y utiliza inglés como alternativa.

    Si no existe una opción en español o inglés, se admite el título original
    cuando usa alfabeto latino. Si tampoco es legible, devuelve None.
    """

    data = dict(data)

    if media_type == "movie":
        title_key = "title"
        original_key = "original_title"
    else:
        title_key = "name"
        original_key = "original_name"

    title = data.get(title_key)
    original_title = data.get(original_key)
    original_language = data.get("original_language")

    if (
        title
        and original_title
        and title != original_title
    ):
        return data, "es"

    if original_language == "es" and title:
        return data, "es"

    if media_type == "movie":
        english_data = client.movie_details(
            data["id"],
            language="en-US",
        )
    else:
        english_data = client.series_details(
            data["id"],
            language="en-US",
        )

    english_title = english_data.get(title_key)
    english_original = english_data.get(original_key)

    if (
        english_title
        and (
            original_language == "en"
            or english_title != english_original
        )
    ):
        data[title_key] = english_title

        if not data.get("overview"):
            data["overview"] = english_data.get("overview")

        return data, "en"

    if original_title and has_latin_letters(original_title):
        data[title_key] = original_title

        if not data.get("overview"):
            data["overview"] = english_data.get("overview")

        return data, "original"

    return None, None
