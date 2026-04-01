from __future__ import annotations

import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from PIL import Image
from sklearn.metrics import (
    classification_report,
    confusion_matrix,
    ConfusionMatrixDisplay,
)
from tensorflow import keras
from tensorflow.keras.preprocessing.image import ImageDataGenerator

MODEL_PATH = "output_exp/steganalysis_model.keras"
TEST_DIR = "dataset_exp/test"
OUTPUT_DIR = "output_exp"
IMG_SIZE = (256, 256)
BATCH_SIZE = 32

def evaluate_psnr_batch(
    cover_dir: str,
    stego_dir: str,
    max_pairs: int | None = None,
) -> dict:
    cover_files = sorted(Path(cover_dir).glob("*.png"))
    stego_files = sorted(Path(stego_dir).glob("*.png"))

    if max_pairs is not None:
        cover_files = cover_files[:max_pairs]
        stego_files = stego_files[:max_pairs]

    pairs = list(zip(cover_files, stego_files))
    if not pairs:
        raise FileNotFoundError("Не знайдено пар cover/stego для обчислення PSNR та MSE.")

    psnr_values = []
    mse_values = []

    for cover_f, stego_f in pairs:
        with Image.open(cover_f) as img1:
            arr1 = np.array(img1.convert("RGB"), dtype=np.float64)
        with Image.open(stego_f) as img2:
            arr2 = np.array(img2.convert("RGB"), dtype=np.float64)

        mse = np.mean((arr1 - arr2) ** 2)
        mse_values.append(float(mse))

        psnr = 10 * np.log10((255.0 ** 2) / mse) if mse > 0 else float("inf")
        psnr_values.append(float(psnr))

    return {
        "n_pairs": len(pairs),
        "psnr_mean": float(np.mean(psnr_values)),
        "psnr_min": float(np.min(psnr_values)),
        "psnr_max": float(np.max(psnr_values)),
        "mse_mean": float(np.mean(mse_values)),
    }

def plot_confusion_matrix(cm: np.ndarray, output_dir: str) -> None:
    fig, ax = plt.subplots(figsize=(6, 5))
    disp = ConfusionMatrixDisplay(
        confusion_matrix=cm,
        display_labels=["Оригінал (cover)", "Стеганограма (stego)"],
    )
    disp.plot(ax=ax, colorbar=False, cmap="Blues")
    ax.set_title("Матриця плутанини")
    plt.tight_layout()

    path = Path(output_dir) / "confusion_matrix.png"
    plt.savefig(path, dpi=150)
    plt.close()
    print(f"Матриця плутанини збережена: {path}")

def main() -> None:
    output_path = Path(OUTPUT_DIR)
    output_path.mkdir(parents=True, exist_ok=True)

    print("Завантаження моделі...")
    model = keras.models.load_model(MODEL_PATH)

    print("Завантаження тестових даних...")
    datagen = ImageDataGenerator(rescale=1.0 / 255)
    test_gen = datagen.flow_from_directory(
        TEST_DIR,
        target_size=IMG_SIZE,
        batch_size=BATCH_SIZE,
        class_mode="binary",
        shuffle=False,
    )

    print("Оцінка моделі...")
    y_prob = model.predict(test_gen, verbose=1)
    y_pred = (y_prob >= 0.5).astype(int).flatten()
    y_true = test_gen.classes

    report = classification_report(
        y_true,
        y_pred,
        target_names=["cover", "stego"],
        output_dict=True,
    )
    cm = confusion_matrix(y_true, y_pred)

    print("\n--- Результати класифікації ---")
    print(classification_report(
        y_true,
        y_pred,
        target_names=["cover", "stego"],
    ))

    plot_confusion_matrix(cm, OUTPUT_DIR)

    print("Обчислення PSNR та MSE...")
    psnr_stats = evaluate_psnr_batch(
        cover_dir=str(Path(TEST_DIR) / "cover"),
        stego_dir=str(Path(TEST_DIR) / "stego"),
    )
    print(f"  PSNR середнє: {psnr_stats['psnr_mean']:.2f} дБ")
    print(f"  PSNR мін/макс: {psnr_stats['psnr_min']:.2f} / {psnr_stats['psnr_max']:.2f} дБ")
    print(f"  MSE середнє: {psnr_stats['mse_mean']:.4f}")

    results = {
        "classification_report": report,
        "confusion_matrix": cm.tolist(),
        "psnr_stats": psnr_stats,
    }

    results_path = output_path / "evaluation_results.json"
    results_path.write_text(json.dumps(results, indent=4, ensure_ascii=False))
    print(f"\nРезультати збережено: {results_path}")

if __name__ == "__main__":
    main()