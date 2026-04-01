from __future__ import annotations

import argparse
from pathlib import Path

from key_manager import (
    generate_key_pair,
    save_private_key,
    save_public_key,
    load_private_key,
    load_public_key,
)
from signer import create_signature_package
from lsb_steganography import embed_signature_bits
from verifier import verify_document_signature
from utils import (
    validate_supported_document,
    build_signed_output_path,
)

def cmd_generate_keys(args) -> None:
    # Генерує пару ключів ECDSA та зберігає їх у PEM-файли.
    private_key, public_key = generate_key_pair()

    private_key_path = Path(args.private_key)
    public_key_path = Path(args.public_key)

    save_private_key(private_key, str(private_key_path), password=args.password)
    save_public_key(public_key, str(public_key_path))

    print("Ключі успішно згенеровано.")
    print(f"Приватний ключ: {private_key_path}")
    print(f"Відкритий ключ: {public_key_path}")

def cmd_sign(args) -> None:
    # Формує підпис для документа та вбудовує його у файл-контейнер.
    input_path = Path(args.input_file)
    if not input_path.exists():
        raise FileNotFoundError(f"Вхідний файл не знайдено: {input_path}")

    validate_supported_document(input_path)

    private_key = load_private_key(args.private_key, password=args.password)
    package = create_signature_package(str(input_path), private_key)
    signature_bits = package["signature_bits"]

    if args.output_file:
        output_path = Path(args.output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)
    else:
        output_path = build_signed_output_path(input_path)

    embed_signature_bits(
        input_file_path=str(input_path),
        output_file_path=str(output_path),
        signature_bits=signature_bits,
        channels_to_use=args.channels,
    )

    print("Підпис успішно сформовано та вбудовано.")
    print(f"Вхідний файл: {input_path}")
    print(f"Вихідний файл: {output_path}")
    print(f"SHA-256: {package['digest_hex']}")
    print(f"Довжина підпису (біт): {package['signature_bit_length']}")


def cmd_verify(args) -> None:
    # Перевіряє прихований підпис документа.
    input_path = Path(args.input_file)
    if not input_path.exists():
        raise FileNotFoundError(f"Файл для перевірки не знайдено: {input_path}")

    validate_supported_document(input_path)

    public_key = load_public_key(args.public_key)
    result = verify_document_signature(str(input_path), public_key)

    print("Перевірку завершено.")
    print(f"Файл: {result['file_path']}")
    print(f"SHA-256: {result['digest_hex']}")
    print(f"Довжина підпису (біт): {result['signature_bit_length']}")
    print(f"Підпис дійсний: {result['is_valid']}")

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Система прихованого електронного підпису"
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    # generate-keys
    parser_keys = subparsers.add_parser(
        "generate-keys",
        help="Згенерувати пару ключів ECDSA"
    )
    parser_keys.add_argument(
        "--private-key",
        default="keys/private_key.pem",
        help="Шлях для збереження приватного ключа"
    )
    parser_keys.add_argument(
        "--public-key",
        default="keys/public_key.pem",
        help="Шлях для збереження відкритого ключа"
    )
    parser_keys.add_argument(
        "--password",
        default=None,
        help="Пароль для захисту приватного ключа"
    )
    parser_keys.set_defaults(func=cmd_generate_keys)

    # sign
    parser_sign = subparsers.add_parser(
        "sign",
        help="Підписати документ і вбудувати підпис"
    )
    parser_sign.add_argument(
        "--input-file",
        required=True,
        help="Шлях до вхідного документа (.docx, .png, .jpg, .jpeg)"
    )
    parser_sign.add_argument(
        "--output-file",
        default=None,
        help="Шлях до вихідного підписаного документа. Якщо не задано, "
             "буде створено output/signed_<ім'я_файлу>"
    )
    parser_sign.add_argument(
        "--private-key",
        default="keys/private_key.pem",
        help="Шлях до приватного ключа"
    )
    parser_sign.add_argument(
        "--password",
        default=None,
        help="Пароль до приватного ключа"
    )
    parser_sign.add_argument(
        "--channels",
        type=int,
        default=3,
        choices=[1, 2, 3],
        help="Кількість RGB-каналів для LSB-вбудовування"
    )
    parser_sign.set_defaults(func=cmd_sign)

    # verify
    parser_verify = subparsers.add_parser(
        "verify",
        help="Перевірити прихований підпис документа"
    )
    parser_verify.add_argument(
        "--input-file",
        required=True,
        help="Шлях до підписаного документа"
    )
    parser_verify.add_argument(
        "--public-key",
        default="keys/public_key.pem",
        help="Шлях до відкритого ключа"
    )
    parser_verify.set_defaults(func=cmd_verify)

    return parser

def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)

if __name__ == "__main__":
    main()