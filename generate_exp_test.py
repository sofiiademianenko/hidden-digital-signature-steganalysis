from pathlib import Path
from key_manager import load_private_key
from signer import create_signature_package
from lsb_steganography import embed_signature_bits

private_key = load_private_key("keys/private_key.pem", password="123456")
cover_dir = Path("dataset_exp/test/cover")
stego_dir = Path("dataset_exp/test/stego")

for cover_file in sorted(cover_dir.glob("*.png")):
    stego_file = stego_dir / cover_file.name.replace("cover_", "stego_")
    package = create_signature_package(str(cover_file), private_key)
    # Розширений payload — підпис 8 разів
    extended_bits = package["signature_bits"] * 8
    embed_signature_bits(
        input_file_path=str(cover_file),
        output_file_path=str(stego_file),
        signature_bits=extended_bits,
    )
    print(f"Оброблено: {cover_file.name}")

print("Готово!")