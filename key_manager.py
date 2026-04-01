from __future__ import annotations
from pathlib import Path
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec

def generate_key_pair():
    # Генерація пари ключів ECDSA на кривій secp256k1
    private_key = ec.generate_private_key(ec.SECP256K1())
    public_key = private_key.public_key()
    return private_key, public_key

def save_private_key(private_key, file_path: str, password: str | None = None) -> None:
    # Приватний ключ у PEM-файл. Якщо password заданий, ключ зберігається у зашифрованому вигляді.
    path = Path(file_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    if password:
        encryption = serialization.BestAvailableEncryption(password.encode("utf-8"))
    else:
        encryption = serialization.NoEncryption()

    pem_data = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=encryption,
    )
    path.write_bytes(pem_data)

def save_public_key(public_key, file_path: str) -> None:
    # Відкритий ключ у PEM-файл.
    path = Path(file_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    pem_data = public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    path.write_bytes(pem_data)

def load_private_key(file_path: str, password: str | None = None):
    # Приватний ключ із PEM-файлу.
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"Приватний ключ не знайдено: {file_path}")

    pem_data = path.read_bytes()
    return serialization.load_pem_private_key(
        pem_data,
        password=password.encode("utf-8") if password else None,
    )

def load_public_key(file_path: str):
    # Відкритий ключ із PEM-файлу.
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"Відкритий ключ не знайдено: {file_path}")

    pem_data = path.read_bytes()
    return serialization.load_pem_public_key(pem_data)

if __name__ == "__main__":
    private_key, public_key = generate_key_pair()

    save_private_key(private_key, "keys/private_key.pem", password="123456")
    save_public_key(public_key, "keys/public_key.pem")

    print("Ключі успішно згенеровано та збережено.")
    print("Приватний ключ: keys/private_key.pem")
    print("Відкритий ключ: keys/public_key.pem")