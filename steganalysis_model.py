from __future__ import annotations

import random
import numpy as np
import tensorflow as tf
from tensorflow import keras
from tensorflow.keras import layers

IMG_SIZE = (256, 256)
BATCH_SIZE = 32
EPOCHS = 30
SEED = 42


def set_seed(seed: int = SEED) -> None:
    random.seed(seed)
    np.random.seed(seed)
    tf.random.set_seed(seed)


def build_model(input_shape: tuple = (256, 256, 3)) -> keras.Model:
    inputs = keras.Input(shape=input_shape)

    # HPF-шар: підсилює сліди LSB-вбудовування
    # Ядро Лапласа — виділяє різкі зміни між сусідніми пікселями
    hpf_kernel = np.array([
        [-1, -1, -1],
        [-1,  8, -1],
        [-1, -1, -1]
    ], dtype=np.float32) / 8.0

    # Форма ваг для Conv2D: (height, width, in_channels, out_channels)
    # Однаковий фільтр до кожного з 3 каналів -> 3 вихідних карти
    kernel_weights = np.zeros((3, 3, 3, 3), dtype=np.float32)
    for i in range(3):
        kernel_weights[:, :, i, i] = hpf_kernel

    hpf_conv = layers.Conv2D(
        filters=3,
        kernel_size=3,
        padding="same",
        use_bias=False,
        trainable=False,  # ваги HPF не навчаються
        name="hpf_filter",
    )
    x = hpf_conv(inputs)
    hpf_conv.set_weights([kernel_weights])

    # Блок 1
    x = layers.Conv2D(32, (3, 3), activation="relu", padding="same")(x)
    x = layers.BatchNormalization()(x)
    x = layers.MaxPooling2D((2, 2))(x)

    # Блок 2
    x = layers.Conv2D(64, (3, 3), activation="relu", padding="same")(x)
    x = layers.BatchNormalization()(x)
    x = layers.MaxPooling2D((2, 2))(x)

    # Блок 3
    x = layers.Conv2D(128, (3, 3), activation="relu", padding="same")(x)
    x = layers.BatchNormalization()(x)
    x = layers.MaxPooling2D((2, 2))(x)

    # Класифікатор
    x = layers.GlobalAveragePooling2D()(x)
    x = layers.Dense(128, activation="relu")(x)
    x = layers.Dropout(0.5)(x)
    outputs = layers.Dense(1, activation="sigmoid")(x)

    model = keras.Model(inputs, outputs, name="steganalysis_hpf_cnn")
    model.compile(
        optimizer=keras.optimizers.Adam(learning_rate=1e-4),
        loss="binary_crossentropy",
        metrics=["accuracy"],
    )
    return model


def predict_single_image(
    model: keras.Model,
    image_path: str,
    img_size: tuple = IMG_SIZE,
) -> dict:
    from tensorflow.keras.preprocessing import image as keras_image
    img = keras_image.load_img(image_path, target_size=img_size)
    img_array = keras_image.img_to_array(img) / 255.0
    img_array = np.expand_dims(img_array, axis=0)
    prob = float(model.predict(img_array, verbose=0)[0][0])
    return {
        "file": image_path,
        "probability_stego": round(prob, 4),
        "prediction": "стеганограма" if prob >= 0.5 else "оригінал",
    }


if __name__ == "__main__":
    set_seed()
    model = build_model()
    model.summary()
    print(f"\nКількість параметрів: {model.count_params():,}")