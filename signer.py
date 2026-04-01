from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Dict, Any

from PIL import Image
from docx import Document
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import ec

from utils import validate_supported_document, save_json

def normalize_docx(file_path: str) -> bytes:
    """
    Нормалізує DOCX-документ:
    - зчитує текст абзаців;
    - прибирає зайві пробіли;
    - формує стабільне байтове представлення.
    Хешується текстовий вміст документа.
    """
    doc = Document(file_path)

    paragraphs = []
    for paragraph in doc.paragraphs:
        text = " ".join(paragraph.text.split())
        if text:
            paragraphs.append(text)

    normalized_text = "\n".join(paragraphs)
    return normalized_text.encode("utf-8")

def normalize_image(file_path: str, lsb_channels: int = 3) -> bytes:
    """
    Нормалізує PNG/JPEG-зображення:
    - відкриває файл;
    - переводить у RGB;
    - обнуляє LSB у тих каналах, що використовуються для вбудовування;
    - серіалізує розмір та піксельні дані.
    Це робить хеш незалежним від прихованого підпису, вбудованого методом LSB.
    """
    with Image.open(file_path) as img:
        img = img.convert("RGB")
        width, height = img.size
        pixel_access = img.load()

        normalized_pixels = []

        for y in range(height):
            for x in range(width):
                r, g, b = pixel_access[x, y]
                channels = [r, g, b]

                for i in range(min(lsb_channels, 3)):
                    channels[i] = channels[i] & ~1

                normalized_pixels.extend(channels)

    header = f"{width}x{height}|RGB|LSB{lsb_channels}|".encode("utf-8")
    return header + bytes(normalized_pixels)

def normalize_document(file_path: str) -> bytes:
    """
    Визначає тип документа та виконує нормалізацію.
    Підтримуються:
    - DOCX
    - PNG
    - JPEG / JPG
    """
    validate_supported_document(file_path)
    suffix = Path(file_path).suffix.lower()

    if suffix == ".docx":
        return normalize_docx(file_path)

    if suffix in {".png", ".jpg", ".jpeg"}:
        return normalize_image(file_path, lsb_channels=3)

    raise ValueError(f"Непідтримуваний формат файлу: {suffix}")


def compute_sha256(data: bytes) -> bytes:
    # Обчислює SHA-256 від байтового представлення документа.
    return hashlib.sha256(data).digest()


def sign_hash(private_key, digest: bytes) -> bytes:
    # Формує ECDSA-підпис для вже обчисленого хеш-значення.
    signature = private_key.sign(
        digest,
        ec.ECDSA(hashes.SHA256())
    )
    return signature


def signature_to_bits(signature: bytes) -> str:
    # Перетворює підпис у бітовий рядок.
    return "".join(f"{byte:08b}" for byte in signature)


def bits_to_signature(bit_string: str) -> bytes:
    # Перетворює бітовий рядок назад у байти підпису.
    if len(bit_string) % 8 != 0:
        raise ValueError("Довжина бітового рядка повинна бути кратною 8.")

    return bytes(
        int(bit_string[i:i + 8], 2)
        for i in range(0, len(bit_string), 8)
    )

def create_signature_package(file_path: str, private_key) -> Dict[str, Any]:
    """
    Повний цикл формування підпису:
    1. Нормалізація документа
    2. Обчислення SHA-256
    3. Формування ECDSA-підпису
    4. Підготовка даних для вбудовування
    Повертає словник з усіма потрібними службовими даними.
    """
    normalized_data = normalize_document(file_path)
    digest = compute_sha256(normalized_data)
    signature = sign_hash(private_key, digest)
    signature_bits = signature_to_bits(signature)

    return {
        "file_path": file_path,
        "normalized_data": normalized_data,
        "digest_bytes": digest,
        "digest_hex": digest.hex(),
        "signature_bytes": signature,
        "signature_hex": signature.hex(),
        "signature_bits": signature_bits,
        "signature_bit_length": len(signature_bits),
    }


def save_signature_info(package: Dict[str, Any], output_path: str) -> None:
    # Зберігає службову інформацію про підпис у JSON.
    data_to_save = {
        "file_path": package["file_path"],
        "digest_hex": package["digest_hex"],
        "signature_hex": package["signature_hex"],
        "signature_bit_length": package["signature_bit_length"],
    }

    save_json(data_to_save, output_path)

if __name__ == "__main__":
    from key_manager import load_private_key

    test_file = "test_data/sample.png"
    # test_file = "test_data/sample.docx"

    private_key = load_private_key("keys/private_key.pem", password="123456")

    package = create_signature_package(test_file, private_key)

    print("Файл:", package["file_path"])
    print("SHA-256:", package["digest_hex"])
    print("Довжина підпису (біт):", package["signature_bit_length"])
    print("Перші 64 біти підпису:", package["signature_bits"][:64])

    save_signature_info(package, "output/signature_info.json")
    print("Інформацію про підпис збережено у output/signature_info.json")