from __future__ import annotations

import argparse
from datetime import datetime
from pathlib import Path


SOURCE_TYPES = {
    ".py": "python",
    ".html": "html",
    ".css": "css",
    ".js": "javascript",
}

IGNORED_DIRS = {
    ".git",
    ".idea",
    ".vscode",
    ".venv",
    "venv",
    "env",
    "__pycache__",
    "node_modules",
    "instance",
    "dist",
    "build",
}

DEFAULT_OUTPUT = Path("documentation/sources/PROJECT_SNAPSHOT.md")


def parse_args():
    parser = argparse.ArgumentParser(
        description="Exporta el código del proyecto a un único Markdown."
    )
    parser.add_argument(
        "--root",
        type=Path,
        default=Path.cwd(),
        help="Raíz del proyecto. Por defecto, el directorio actual.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help="Markdown de salida relativo a la raíz del proyecto.",
    )
    return parser.parse_args()


def source_files(root, output):
    files = []

    for path in root.rglob("*"):
        if not path.is_file():
            continue

        relative = path.relative_to(root)

        if any(part in IGNORED_DIRS for part in relative.parts[:-1]):
            continue

        if path.suffix.lower() not in SOURCE_TYPES:
            continue

        if path.resolve() == output.resolve():
            continue

        files.append(path)

    return sorted(
        files,
        key=lambda path: path.relative_to(root).as_posix().lower(),
    )


def read_source(path):
    for encoding in ("utf-8", "utf-8-sig", "cp1252", "latin-1"):
        try:
            return path.read_text(encoding=encoding)
        except UnicodeDecodeError:
            pass

    raise RuntimeError(f"No se pudo leer {path}")


def build_snapshot(root, files):
    generated = datetime.now().astimezone()
    contents = []
    counts = {extension: 0 for extension in SOURCE_TYPES}
    total_lines = 0

    for path in files:
        content = read_source(path)
        line_count = len(content.splitlines())
        counts[path.suffix.lower()] += 1
        total_lines += line_count
        contents.append((path, content, line_count))

    lines = [
        "# Snapshot de código — Netflix del Temu",
        "",
        "> Archivo generado automáticamente para revisión técnica y visual del proyecto.",
        "",
        "## Información",
        "",
        f"- Generado: `{generated:%Y-%m-%d %H:%M:%S %z}`",
        f"- Raíz: `{root}`",
        f"- Archivos incluidos: **{len(files)}**",
        f"- Líneas aproximadas: **{total_lines}**",
        "",
        "## Resumen por tipo",
        "",
    ]

    for extension in SOURCE_TYPES:
        lines.append(f"- `{extension}`: **{counts[extension]}**")

    lines.extend(["", "## Archivos incluidos", ""])

    for path in files:
        lines.append(f"- `{path.relative_to(root).as_posix()}`")

    lines.extend(["", "---", "", "# Código completo", ""])

    for path, content, line_count in contents:
        relative = path.relative_to(root).as_posix()
        language = SOURCE_TYPES[path.suffix.lower()]
        lines.extend(
            [
                "",
                f"## `{relative}`",
                "",
                f"**Líneas:** {line_count}",
                "",
                f"```{language}",
                content.rstrip(),
                "```",
            ]
        )

    return "\n".join(lines).rstrip() + "\n"


def main():
    args = parse_args()
    root = args.root.resolve()

    if not root.is_dir():
        raise SystemExit(f"La raíz no es una carpeta válida: {root}")

    output = args.output
    if not output.is_absolute():
        output = root / output

    files = source_files(root, output)

    if not files:
        raise SystemExit("No se encontraron archivos de código.")

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(build_snapshot(root, files), encoding="utf-8")

    print("Snapshot generado correctamente.")
    print(f"Archivos incluidos: {len(files)}")
    print(f"Salida: {output}")
    print(f"Tamaño: {output.stat().st_size / 1024:.1f} KB")


if __name__ == "__main__":
    main()
