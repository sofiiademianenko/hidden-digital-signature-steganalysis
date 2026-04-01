from __future__ import annotations

import json
from pathlib import Path
from typing import Any

SUPPORTED_DOCUMENT_EXTENSIONS = {".docx", ".png", ".jpg", ".jpeg"}
SUPPORTED_IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg"}

def ensure_parent_dir(file_path: str | Path) -> Path:
    # Створює батьківську директорію для файлу, якщо вона не існує. Повертає Path-об'єкт.
    path = Path(file_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    return path

def get_file_extension(file_path: str | Path) -> str:
    # Повертає розширення файлу в нижньому регістрі.
    return Path(file_path).suffix.lower()

def is_supported_document(file_path: str | Path) -> bool:
    # Перевіряє, чи підтримується формат документа.
    return get_file_extension(file_path) in SUPPORTED_DOCUMENT_EXTENSIONS

def is_supported_image(file_path: str | Path) -> bool:
    # Перевіряє, чи є файл підтримуваним зображенням.
    return get_file_extension(file_path) in SUPPORTED_IMAGE_EXTENSIONS

def validate_supported_document(file_path: str | Path) -> None:
    # Піднімає помилку, якщо формат документа не підтримується.
    extension = get_file_extension(file_path)
    if extension not in SUPPORTED_DOCUMENT_EXTENSIONS:
        raise ValueError(
            f"Непідтримуваний формат файлу: {extension}. "
            f"Підтримуються: {', '.join(sorted(SUPPORTED_DOCUMENT_EXTENSIONS))}"
        )

def build_signed_output_path(input_file: str | Path, output_dir: str | Path = "output") -> Path:
    # Формує стандартне ім'я вихідного підписаного файлу.
    input_path = Path(input_file)
    output_directory = Path(output_dir)
    output_directory.mkdir(parents=True, exist_ok=True)
    return output_directory / f"signed_{input_path.name}"

def save_json(data: dict[str, Any], file_path: str | Path) -> None:
    # Зберігає словник у JSON-файл.
    path = ensure_parent_dir(file_path)
    path.write_text(
        json.dumps(data, ensure_ascii=False, indent=4),
        encoding="utf-8"
    )

def load_json(file_path: str | Path) -> dict[str, Any]:
    # Завантажує словник із JSON-файлу.
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"JSON-файл не знайдено: {file_path}")

    return json.loads(path.read_text(encoding="utf-8"))

def file_exists(file_path: str | Path) -> bool:
    # Перевіряє, чи існує файл.
    return Path(file_path).exists()

def describe_file_type(file_path: str | Path) -> str:
    # Повертає короткий опис типу файлу.
    extension = get_file_extension(file_path)

    if extension == ".docx":
        return "DOCX-документ"
    if extension == ".png":
        return "PNG-зображення"
    if extension in {".jpg", ".jpeg"}:
        return "JPEG-зображення"
    return "Невідомий тип файлу"


if __name__ == "__main__":
    test_file = "test_data/sample.docx"

    print("Розширення:", get_file_extension(test_file))
    print("Тип файлу:", describe_file_type(test_file))
    print("Підтримується:", is_supported_document(test_file))
    print("Вихідний файл:", build_signed_output_path(test_file))