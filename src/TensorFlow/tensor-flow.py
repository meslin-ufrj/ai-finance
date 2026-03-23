import tensorflow as tf
from tensorflow import keras

model = keras.Sequential([
    keras.layers.Dense(10, activation='relu'),
    keras.layers.Dense(1)
])

model.compile(optimizer='adam', loss='mse')
# Tensores
a = tf.constant(2)
b = tf.constant(3)

# Operação
c = a + b

print(c)  # tf.Tensor(5, shape=(), dtype=int32)