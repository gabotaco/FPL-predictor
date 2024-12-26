import time
import tensorflow as tf
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import LSTM, Dense, Dropout, Input
from tensorflow.keras.regularizers import l2
from tensorflow.keras.callbacks import Callback

tf.keras.backend.set_floatx('float64')


def make_model(time_steps, amount_of_features, n_neurons=64, dropout_rate=0.5, n_hidden_layers=1,
               n_neurons_last_layer=128):
    layers = [Input((time_steps, amount_of_features))]
    for _ in range(0, n_hidden_layers):
        layers.append(LSTM(n_neurons, return_sequences=True, kernel_regularizer=l2(0.001), bias_regularizer=l2(0.001)))
        layers.append(Dropout(dropout_rate))

    layers.append(LSTM(n_neurons, return_sequences=False, kernel_regularizer=l2(0.001), bias_regularizer=l2(0.001)))
    layers.append(Dropout(dropout_rate))

    layers.append(
        Dense(n_neurons_last_layer, activation='relu', kernel_regularizer=l2(0.001), bias_regularizer=l2(0.001)))
    layers.append(Dense(units=1, activation='relu'))

    return Sequential(layers=layers)


def split_df_to_train_test(x, y, split_rate=0.8):
    amount_of_data = x.shape[0]

    split_level = int(amount_of_data * split_rate)

    return x[:split_level], y[:split_level], x[split_level:], y[split_level:]


class LimitTrainingTime(Callback):
    def __init__(self, max_time_s):
        super().__init__()
        self.max_time_s = max_time_s
        self.start_time = None

    def on_train_begin(self, _):
        self.start_time = time.time()

    def on_train_batch_end(self, _, __):
        now = time.time()
        if now - self.start_time >= self.max_time_s:
            self.model.stop_training = True
