from __future__ import annotations

from typing import Dict, Any

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.exceptions import InvalidSignature

from signer import normalize_document, compute_sha256, bits_to_signature
from lsb_steganography import extract_signature_bits

def verify_signature_bytes(public_key, digest: bytes, signature: bytes) -> bool:
    """
    Перевіряє ECDSA-підпис для заданого хеш-значення.
    Повертає True, якщо підпис дійсний, і False в іншому випадку.
    """
    try:
        public_key.verify(
            signature,
            digest,
            ec.ECDSA(hashes.SHA256())
        )
        return True
    except InvalidSignature:
        return False

def verify_document_signature(file_path: str, public_key) -> Dict[str, Any]:
    """
    Повний цикл перевірки прихованого підпису:
    1. Витягнення підпису з документа/зображення
    2. Нормалізація документа
    3. Обчислення SHA-256
    4. Перевірка ECDSA-підпису

    Повертає словник із результатами перевірки.
    """
    # Витягнення прихованного підпису
    signature_bits = extract_signature_bits(file_path)
    signature_bytes = bits_to_signature(signature_bits)

    # Нормалізація поточного документа
    normalized_data = normalize_document(file_path)
    digest = compute_sha256(normalized_data)

    # Перевірка підпису
    is_valid = verify_signature_bytes(public_key, digest, signature_bytes)

    return {
        "file_path": file_path,
        "digest_hex": digest.hex(),
        "signature_bit_length": len(signature_bits),
        "signature_hex": signature_bytes.hex(),
        "is_valid": is_valid,
    }

if __name__ == "__main__":
    from key_manager import load_public_key

    # Файл для перевірки:
    file_to_verify = "output/embedded_sample.docx"
    # file_to_verify = "output/embedded_sample.png"

    public_key = load_public_key("keys/public_key.pem")

    result = verify_document_signature(file_to_verify, public_key)

    print("Файл:", result["file_path"])
    print("SHA-256:", result["digest_hex"])
    print("Довжина підпису (біт):", result["signature_bit_length"])
    print("Підпис дійсний:", result["is_valid"])