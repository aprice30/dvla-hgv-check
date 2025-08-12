import tensorflow as tf
from tensorflow.keras import layers, models
import pathlib

# Paths
DATASET_DIR = pathlib.Path("data/road_images")
MODEL_PATH = "road_model"

# Parameters
IMG_SIZE = (128, 128)
BATCH_SIZE = 32
EPOCHS = 10

# Load dataset
train_ds = tf.keras.utils.image_dataset_from_directory(
    DATASET_DIR,
    validation_split=0.2,
    subset="training",
    seed=123,
    image_size=IMG_SIZE,
    batch_size=BATCH_SIZE
)

val_ds = tf.keras.utils.image_dataset_from_directory(
    DATASET_DIR,
    validation_split=0.2,
    subset="validation",
    seed=123,
    image_size=IMG_SIZE,
    batch_size=BATCH_SIZE
)

# Prefetch for performance
AUTOTUNE = tf.data.AUTOTUNE
train_ds = train_ds.cache().shuffle(1000).prefetch(buffer_size=AUTOTUNE)
val_ds = val_ds.cache().prefetch(buffer_size=AUTOTUNE)

# Normalization layer
normalization_layer = layers.Rescaling(1./255)

# Simple CNN model
model = models.Sequential([
    normalization_layer,
    layers.Conv2D(32, 3, activation='relu'),
    layers.MaxPooling2D(),
    layers.Conv2D(64, 3, activation='relu'),
    layers.MaxPooling2D(),
    layers.Flatten(),
    layers.Dense(128, activation='relu'),
    layers.Dense(len(train_ds.class_names), activation='softmax')
])

# Compile
model.compile(optimizer='adam',
              loss='sparse_categorical_crossentropy',
              metrics=['accuracy'])

# Train
model.fit(train_ds, validation_data=val_ds, epochs=EPOCHS)

# Save model
model.save(MODEL_PATH)
print(f"Model saved to {MODEL_PATH}")
print(f"Classes: {train_ds.class_names}")
