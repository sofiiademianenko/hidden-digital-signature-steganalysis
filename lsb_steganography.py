from __future__ import annotations

import os
import tempfile
import zipfile
from pathlib import Path
from typing import Tuple

from PIL import Image

SUPPORTED_IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg"}

def int_to_bits(value: int, bit_length: int) -> str:
    # Перетворює ціле число у бітовий рядок фіксованої довжини.
    return format(value, f"0{bit_length}b")

def bits_to_int(bit_string: str) -> int:
    # Перетворює бітовий рядок у ціле число.
    return int(bit_string, 2)

def bytes_to_bits(data: bytes) -> str:
    # Перетворює байти у бітовий рядок.
    return "".join(f"{byte:08b}" for byte in data)


def bits_to_bytes(bit_string: str) -> bytes:
    # Перетворює бітовий рядок у байти.
    if len(bit_string) % 8 != 0:
        raise ValueError("Довжина бітового рядка повинна бути кратною 8.")
    return bytes(int(bit_string[i:i + 8], 2) for i in range(0, len(bit_string), 8))

def get_image_pixels(img: Image.Image) -> list[tuple[int, int, int]]:
    # Повертає список пікселів RGB без використання getdata().
    width, height = img.size
    pixel_access = img.load()
    return [pixel_access[x, y] for y in range(height) for x in range(width)]


def get_image_capacity_bits(image: Image.Image, channels_to_use: int = 3) -> int:
    # Обчислює ємність контейнера в бітах. За замовчуванням використовується 3 канали RGB.
    width, height = image.size
    return width * height * channels_to_use


def embed_bits_in_image(
    input_image_path: str,
    output_image_path: str,
    payload_bits: str,
    channels_to_use: int = 3
) -> None:
    """
    Вбудовує payload_bits у зображення методом LSB.
    Спочатку вбудовується 32-бітова довжина payload, потім сам payload.
    """
    with Image.open(input_image_path) as img:
        img = img.convert("RGB")
        img_size = img.size
        pixels = get_image_pixels(img)

    header_bits = int_to_bits(len(payload_bits), 32)
    full_bits = header_bits + payload_bits

    capacity = len(pixels) * channels_to_use
    if len(full_bits) > capacity:
        raise ValueError(
            f"Недостатня ємність контейнера: потрібно {len(full_bits)} біт, доступно {capacity} біт."
        )

    bit_index = 0
    new_pixels = []

    for r, g, b in pixels:
        channels = [r, g, b]

        for i in range(channels_to_use):
            if bit_index < len(full_bits):
                channels[i] = (channels[i] & ~1) | int(full_bits[bit_index])
                bit_index += 1

        new_pixels.append(tuple(channels))

    output_img = Image.new("RGB", img_size)
    output_img.putdata(new_pixels)

    suffix = Path(output_image_path).suffix.lower()
    if suffix in {".jpg", ".jpeg"}:
        # JPEG стискає з втратами, тому для стабільної роботи LSB краще PNG.
        output_img.save(output_image_path, quality=100, subsampling=0)
    else:
        output_img.save(output_image_path)


def extract_bits_from_image(
    input_image_path: str,
    channels_to_use: int = 3
) -> str:
    # Витягує payload_bits із зображення. Перші 32 біти — довжина корисного навантаження.
    with Image.open(input_image_path) as img:
        img = img.convert("RGB")
        pixels = get_image_pixels(img)

    extracted_bits = []

    for r, g, b in pixels:
        channels = [r, g, b]
        for i in range(channels_to_use):
            extracted_bits.append(str(channels[i] & 1))

    extracted_bits = "".join(extracted_bits)

    header_bits = extracted_bits[:32]
    payload_length = bits_to_int(header_bits)

    start = 32
    end = 32 + payload_length
    payload_bits = extracted_bits[start:end]

    if len(payload_bits) != payload_length:
        raise ValueError("Не вдалося коректно витягти приховані дані.")

    return payload_bits

def create_service_image(
    output_path: str,
    width: int = 200,
    height: int = 200,
    color: Tuple[int, int, int] = (255, 255, 255)
) -> None:
    # Створює службове зображення для DOCX, якщо в документі немає жодного зображення.
    img = Image.new("RGB", (width, height), color=color)
    img.save(output_path, format="PNG")


def find_or_create_docx_media_image(extract_dir: str) -> str:
    """
    Знаходить перше зображення у word/media.
    Якщо зображення відсутнє — створює службове service_image.png.
    Повертає шлях до файлу-зображення.
    """
    media_dir = Path(extract_dir) / "word" / "media"
    media_dir.mkdir(parents=True, exist_ok=True)

    for file_path in media_dir.iterdir():
        if file_path.suffix.lower() in SUPPORTED_IMAGE_EXTENSIONS:
            return str(file_path)

    service_image_path = media_dir / "service_image.png"
    create_service_image(str(service_image_path))
    return str(service_image_path)


def repack_docx_from_directory(extract_dir: str, output_docx_path: str) -> None:
    # Збирає DOCX-файл назад із розпакованої директорії.
    output_path = Path(output_docx_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with zipfile.ZipFile(output_docx_path, "w", zipfile.ZIP_DEFLATED) as docx_zip:
        for root, _, files in os.walk(extract_dir):
            for file_name in files:
                full_path = Path(root) / file_name
                relative_path = full_path.relative_to(extract_dir)
                docx_zip.write(full_path, relative_path)


def embed_bits_in_docx(
    input_docx_path: str,
    output_docx_path: str,
    payload_bits: str,
    channels_to_use: int = 3
) -> None:
    """
    Вбудовує payload_bits у DOCX:
    - розпаковує DOCX;
    - знаходить або створює службове зображення;
    - вбудовує у нього біти;
    - збирає DOCX назад.
    """
    with tempfile.TemporaryDirectory() as tmp_dir:
        extract_dir = Path(tmp_dir) / "docx_contents"
        extract_dir.mkdir(parents=True, exist_ok=True)

        with zipfile.ZipFile(input_docx_path, "r") as docx_zip:
            docx_zip.extractall(extract_dir)

        image_path = find_or_create_docx_media_image(str(extract_dir))

        # Якщо зображення JPEG, перетворюємо його на PNG для надійнішого LSB
        image_suffix = Path(image_path).suffix.lower()
        if image_suffix in {".jpg", ".jpeg"}:
            png_path = str(Path(image_path).with_suffix(".png"))
            with Image.open(image_path) as img:
                img.convert("RGB").save(png_path, format="PNG")
            os.remove(image_path)
            image_path = png_path

        embed_bits_in_image(image_path, image_path, payload_bits, channels_to_use=channels_to_use)
        repack_docx_from_directory(str(extract_dir), output_docx_path)


def extract_bits_from_docx(
    input_docx_path: str,
    channels_to_use: int = 3
) -> str:
    # Витягує payload_bits із першого доступного зображення у word/media DOCX.
    with tempfile.TemporaryDirectory() as tmp_dir:
        extract_dir = Path(tmp_dir) / "docx_contents"
        extract_dir.mkdir(parents=True, exist_ok=True)

        with zipfile.ZipFile(input_docx_path, "r") as docx_zip:
            docx_zip.extractall(extract_dir)

        media_dir = extract_dir / "word" / "media"
        if not media_dir.exists():
            raise ValueError("У DOCX не знайдено каталог word/media.")

        image_candidates = [
            p for p in media_dir.iterdir()
            if p.suffix.lower() in SUPPORTED_IMAGE_EXTENSIONS
        ]

        if not image_candidates:
            raise ValueError("У DOCX не знайдено зображення для витягнення підпису.")

        service_candidates = [p for p in image_candidates if p.name == "service_image.png"]
        target_image = service_candidates[0] if service_candidates else image_candidates[0]

        return extract_bits_from_image(str(target_image), channels_to_use=channels_to_use)


def embed_signature_bits(
    input_file_path: str,
    output_file_path: str,
    signature_bits: str,
    channels_to_use: int = 3
) -> None:
    """
    Універсальна функція вбудовування:
    - PNG/JPEG -> безпосередньо в зображення
    - DOCX -> у зображення в word/media
    """
    suffix = Path(input_file_path).suffix.lower()

    if suffix in {".png", ".jpg", ".jpeg"}:
        embed_bits_in_image(input_file_path, output_file_path, signature_bits, channels_to_use)
    elif suffix == ".docx":
        embed_bits_in_docx(input_file_path, output_file_path, signature_bits, channels_to_use)
    else:
        raise ValueError(f"Непідтримуваний формат файлу: {suffix}")


def extract_signature_bits(
    input_file_path: str,
    channels_to_use: int = 3
) -> str:
    """
    Універсальна функція витягнення:
    - PNG/JPEG -> із зображення
    - DOCX -> із зображення в word/media
    """
    suffix = Path(input_file_path).suffix.lower()

    if suffix in {".png", ".jpg", ".jpeg"}:
        return extract_bits_from_image(input_file_path, channels_to_use)
    elif suffix == ".docx":
        return extract_bits_from_docx(input_file_path, channels_to_use)
    else:
        raise ValueError(f"Непідтримуваний формат файлу: {suffix}")

if __name__ == "__main__":
    from signer import create_signature_package
    from key_manager import load_private_key

    private_key = load_private_key("keys/private_key.pem", password="123456")

    input_file = "test_data/sample.docx"
    # input_file = "test_data/sample.png"

    package = create_signature_package(input_file, private_key)
    signature_bits = package["signature_bits"]

    output_dir = Path("output")
    output_dir.mkdir(parents=True, exist_ok=True)

    output_file = output_dir / f"embedded_{Path(input_file).name}"

    embed_signature_bits(
        input_file_path=input_file,
        output_file_path=str(output_file),
        signature_bits=signature_bits
    )

    extracted_bits = extract_signature_bits(str(output_file))

    print("Вхідний файл:", input_file)
    print("Вихідний файл:", output_file)
    print("Довжина вбудованого підпису (біт):", len(signature_bits))
    print("Довжина витягнутого підпису (біт):", len(extracted_bits))
    print("Підписи збігаються:", signature_bits == extracted_bits)