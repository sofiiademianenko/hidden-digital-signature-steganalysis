from __future__ import annotations

import json
import random
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import tensorflow as tf
from tensorflow import keras
from tensorflow.keras.preprocessing.image import ImageDataGenerator

from steganalysis_model import build_model

TRAIN_DIR = "dataset_exp/train"
VAL_DIR = "dataset_exp/val"
OUTPUT_DIR = "output_exp"

IMG_SIZE = (256, 256)
BATCH_SIZE = 32
EPOCHS = 30
SEED = 42

def set_seed(seed: int = SEED) -> None:
    random.seed(seed)
    np.random.seed(seed)
    tf.random.set_seed(seed)

def load_data(train_dir: str, val_dir: str, img_size: tuple, batch_size: int):
    train_datagen = ImageDataGenerator(
        rescale=1.0 / 255,
    )

    val_datagen = ImageDataGenerator(
        rescale=1.0 / 255,
    )

    train_gen = train_datagen.flow_from_directory(
        train_dir,
        target_size=img_size,
        batch_size=batch_size,
        class_mode="binary",
        shuffle=True,
        seed=SEED,
    )

    val_gen = val_datagen.flow_from_directory(
        val_dir,
        target_size=img_size,
        batch_size=batch_size,
        class_mode="binary",
        shuffle=False,
    )
    return train_gen, val_gen

def plot_history(history: keras.callbacks.History, output_dir: str) -> None:
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    fig, axes = plt.subplots(1, 2, figsize=(12, 4))

    axes[0].plot(history.history["accuracy"], label="Навчання")
    axes[0].plot(history.history["val_accuracy"], label="Валідація")
    axes[0].set_title("Точність моделі")
    axes[0].set_xlabel("Епоха")
    axes[0].set_ylabel("Точність")
    axes[0].legend()
    axes[0].grid(True)

    axes[1].plot(history.history["loss"], label="Навчання")
    axes[1].plot(history.history["val_loss"], label="Валідація")
    axes[1].set_title("Функція втрат")
    axes[1].set_xlabel("Епоха")
    axes[1].set_ylabel("Втрати")
    axes[1].legend()
    axes[1].grid(True)

    plt.tight_layout()
    plot_path = output_path / "training_history.png"
    plt.savefig(plot_path, dpi=150)
    plt.close()
    print(f"Графік навчання збережено: {plot_path}")

def save_history(history: keras.callbacks.History, output_dir: str) -> None:
    path = Path(output_dir) / "training_history.json"
    data = {k: [float(v) for v in vals] for k, vals in history.history.items()}
    path.write_text(json.dumps(data, indent=4, ensure_ascii=False))
    print(f"Історію навчання збережено: {path}")

def main() -> None:
    set_seed()
    Path(OUTPUT_DIR).mkdir(parents=True, exist_ok=True)

    print("Завантаження датасету...")
    train_gen, val_gen = load_data(TRAIN_DIR, VAL_DIR, IMG_SIZE, BATCH_SIZE)

    print(f"  Навчальна вибірка: {train_gen.samples} зображень")
    print(f"  Валідаційна вибірка: {val_gen.samples} зображень")
    print(f"  Класи: {train_gen.class_indices}")

    print("\nПобудова моделі...")
    model = build_model(input_shape=(*IMG_SIZE, 3))
    model.summary()

    model_path = str(Path(OUTPUT_DIR) / "steganalysis_model.keras")

    callbacks = [
        keras.callbacks.ModelCheckpoint(
            model_path,
            save_best_only=True,
            monitor="val_accuracy",
            verbose=1,
        ),
        keras.callbacks.EarlyStopping(
            monitor="val_loss",
            patience=6,
            restore_best_weights=True,
            verbose=1,
        ),
        keras.callbacks.ReduceLROnPlateau(
            monitor="val_loss",
            factor=0.5,
            patience=3,
            min_lr=1e-6,
            verbose=1,
        ),
    ]

    print("\nНавчання моделі...")
    history = model.fit(
        train_gen,
        validation_data=val_gen,
        epochs=EPOCHS,
        callbacks=callbacks,
    )

    plot_history(history, OUTPUT_DIR)
    save_history(history, OUTPUT_DIR)

    best_val_acc = max(history.history["val_accuracy"])
    print(
        f"\nНайкраща точність на валідації: "
        f"{best_val_acc:.4f} ({best_val_acc * 100:.2f}%)"
    )
    print(f"Модель збережено: {model_path}")

if __name__ == "__main__":
    main()