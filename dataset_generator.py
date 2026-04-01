from __future__ import annotations

import random
from pathlib import Path
from PIL import Image

from key_manager import (
    generate_key_pair,
    save_private_key,
    save_public_key,
    load_private_key,
)
from signer import create_signature_package
from lsb_steganography import embed_signature_bits

IMG_SIZE = (256, 256)
SEED = 42

def prepare_boss_images(
    boss_dir: str,
    prepared_dir: str,
    max_images: int = 1000,
) -> list[Path]:
    """
    Бере зображення з BOSS Base, переводить у RGB, змінює розмір до 256x256
    та зберігає у temporary папку prepared/. Повертає список підготовлених файлів.
    """
    boss_path = Path(boss_dir)
    prepared_path = Path(prepared_dir)
    prepared_path.mkdir(parents=True, exist_ok=True)

    image_files = sorted(
        p for p in boss_path.rglob("*")
        if p.suffix.lower() in {".png", ".pgm", ".bmp", ".jpg", ".jpeg"}
    )[:max_images]

    if not image_files:
        raise FileNotFoundError(
            f"У папці {boss_dir} не знайдено зображень."
        )

    prepared_files: list[Path] = []

    for idx, src_path in enumerate(image_files):
        dst_path = prepared_path / f"img_{idx:05d}.png"
        with Image.open(src_path) as img:
            img = img.convert("RGB")
            img = img.resize(IMG_SIZE, Image.LANCZOS)
            img.save(dst_path, format="PNG")

        prepared_files.append(dst_path)

        if (idx + 1) % 100 == 0:
            print(f"  Оброблено {idx + 1}/{len(image_files)} зображень...")

    print(f"Підготовлено {len(prepared_files)} cover-зображень у {prepared_path}")
    return prepared_files

def split_dataset(
    image_paths: list[Path],
    train_ratio: float = 0.7,
    val_ratio: float = 0.15,
    test_ratio: float = 0.15,
    seed: int = SEED,
) -> dict[str, list[Path]]:
    if abs(train_ratio + val_ratio + test_ratio - 1.0) > 1e-9:
        raise ValueError("Сума train_ratio, val_ratio, test_ratio має дорівнювати 1.0")

    rng = random.Random(seed)
    shuffled = image_paths[:]
    rng.shuffle(shuffled)

    n = len(shuffled)
    n_train = int(n * train_ratio)
    n_val = int(n * val_ratio)

    train_files = shuffled[:n_train]
    val_files = shuffled[n_train:n_train + n_val]
    test_files = shuffled[n_train + n_val:]

    return {
        "train": train_files,
        "val": val_files,
        "test": test_files,
    }

def generate_keys_if_needed(
    private_key_path: str = "keys/private_key.pem",
    public_key_path: str = "keys/public_key.pem",
    password: str = "123456",
) -> None:
    if not Path(private_key_path).exists():
        print("Генерація ключів ECDSA...")
        private_key, public_key = generate_key_pair()
        save_private_key(private_key, private_key_path, password=password)
        save_public_key(public_key, public_key_path)
        print(f"Ключі збережено: {private_key_path}, {public_key_path}")
    else:
        print("Ключі вже існують, пропускаємо генерацію.")

def build_experimental_payload(
    signature_bits: str,
    repeat_factor: int = 1,
    max_payload_bits: int | None = None,
) -> str:
    if repeat_factor < 1:
        raise ValueError("repeat_factor має бути >= 1")

    payload_bits = signature_bits * repeat_factor

    if max_payload_bits is not None:
        payload_bits = payload_bits[:max_payload_bits]

    return payload_bits

def save_cover_and_stego_split(
    split_name: str,
    image_paths: list[Path],
    dataset_dir: str,
    private_key_path: str = "keys/private_key.pem",
    password: str | None = "123456",
    channels: int = 3,
    payload_repeat: int = 8,
    max_payload_bits: int | None = None,
) -> tuple[int, int]:
    """
    Для кожного split:
      - копіює оригінал у dataset/<split>/cover/
      - формує підпис і зберігає стеганограму у dataset/<split>/stego/

    payload_repeat:
      1  -> стандартний експеримент
      8 -> контрольний експеримент зі збільшеним обсягом вбудовування
    """
    private_key = load_private_key(private_key_path, password=password)

    cover_dir = Path(dataset_dir) / split_name / "cover"
    stego_dir = Path(dataset_dir) / split_name / "stego"
    cover_dir.mkdir(parents=True, exist_ok=True)
    stego_dir.mkdir(parents=True, exist_ok=True)

    cover_count = 0
    stego_count = 0

    for idx, src_file in enumerate(image_paths):
        cover_dst = cover_dir / f"cover_{idx:05d}.png"
        stego_dst = stego_dir / f"stego_{idx:05d}.png"

        with Image.open(src_file) as img:
            img = img.convert("RGB")
            img.save(cover_dst, format="PNG")
        cover_count += 1

        package = create_signature_package(str(cover_dst), private_key)

        payload_bits = build_experimental_payload(
            signature_bits=package["signature_bits"],
            repeat_factor=payload_repeat,
            max_payload_bits=max_payload_bits,
        )

        embed_signature_bits(
            input_file_path=str(cover_dst),
            output_file_path=str(stego_dst),
            signature_bits=payload_bits,
            channels_to_use=channels,
        )
        stego_count += 1

        if (idx + 1) % 100 == 0:
            print(
                f"  {split_name}: оброблено {idx + 1}/{len(image_paths)} "
                f"(payload bits = {len(payload_bits)})"
            )

    return cover_count, stego_count


def build_dataset(
    boss_dir: str = "boss_base",
    dataset_dir: str = "dataset",
    prepared_dir: str = "prepared_cover",
    max_images: int = 1000,
    channels: int = 3,
    payload_repeat: int = 1,
    max_payload_bits: int | None = None,
) -> None:
    print("=" * 60)
    print("Крок 1: Підготовка ключів")
    generate_keys_if_needed()

    print("\nКрок 2: Підготовка BOSS Base")
    prepared_files = prepare_boss_images(
        boss_dir=boss_dir,
        prepared_dir=prepared_dir,
        max_images=max_images,
    )

    print("\nКрок 3: Розбиття на train / val / test")
    splits = split_dataset(prepared_files)
    for split_name, files in splits.items():
        print(f"  {split_name}: {len(files)} зображень")

    print("\nКрок 4: Формування cover / stego для кожного split")
    print(f"  Параметр payload_repeat = {payload_repeat}")
    if max_payload_bits is not None:
        print(f"  Максимальна довжина payload = {max_payload_bits} біт")

    summary = {}
    for split_name, files in splits.items():
        cover_n, stego_n = save_cover_and_stego_split(
            split_name=split_name,
            image_paths=files,
            dataset_dir=dataset_dir,
            channels=channels,
            payload_repeat=payload_repeat,
            max_payload_bits=max_payload_bits,
        )
        summary[split_name] = {"cover": cover_n, "stego": stego_n}

    print("\n" + "=" * 60)
    print("Датасет сформовано:")
    for split_name, counts in summary.items():
        print(
            f"  {split_name}: cover={counts['cover']}, "
            f"stego={counts['stego']}"
        )
    print(f"  Розташування: {Path(dataset_dir).resolve()}")
    print("=" * 60)


if __name__ == "__main__":
    build_dataset(
        boss_dir="boss_base",
        dataset_dir="dataset_exp",
        prepared_dir="prepared_cover",
        max_images=9000,
        payload_repeat=8,         # 1 = базовий експеримент, 8 = контрольний
        max_payload_bits=None,
    )