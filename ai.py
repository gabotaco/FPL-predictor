from pmdarima.arima import auto_arima
import numpy as np
from tensorflow.keras.callbacks import EarlyStopping

from lstm_utils import split_df_to_train_test, make_model, LimitTrainingTime

MAX_POINTS = 50
RETRY_POINT = 20
MAX_RETRIES = 5
MAX_DIFF = 3.5

arima_counter = 0
lstm_counter = 0


def do_arima(ts, pred_by):
    global arima_counter
    if arima_counter == MAX_RETRIES:
        raise Exception("Too many ARIMA calls")

    if len(pred_by['games']) == 0:
        return [0, 0]

    has_non_zero = False
    has_same_num = ts[0]

    for gw in ts:
        if has_non_zero and has_same_num is False:
            break

        if gw > 0:
            has_non_zero = True
        if gw != has_same_num:
            has_same_num = False

    if not has_non_zero:
        return [0, 0]

    if has_same_num is not False:
        return [has_same_num, has_same_num]

    print('Training arima...')
    # arima = auto_arima(ts, seasonal=True, m=52)
    arima = auto_arima(ts, seasonal=False)
    print('Making prediction...')

    pred = arima.predict(len(pred_by['games']))

    print('Done!')

    overall = sum(pred)
    next_points = sum(pred[:pred_by['next']])

    if overall / len(pred_by['games']) >= RETRY_POINT or overall / len(pred_by['games']) <= -RETRY_POINT:
        print("RETRY ARIMA")
        print("ts", ts)
        print("overall / len(pred_by['games'])", overall / len(pred_by['games']))
        arima_counter += 1
        return do_arima(ts, pred_by)

    arima_counter = 0
    return [overall, next_points]


def do_lstm(player_data, pred_by):
    global lstm_counter
    if lstm_counter == MAX_RETRIES:
        raise Exception("Too many LSTM calls")

    if len(pred_by['games']) == 0:
        return [0, 0]

    X = []
    y = []
    last_points = None

    for key, value in player_data.items():
        if not key.startswith("GW"):
            continue

        gw_points = value['points']
        gw_diff = value['diff']

        if last_points is None:
            last_points = gw_points
            continue

        X.append([[last_points, gw_diff]])
        y.append([gw_points])

        last_points = gw_points

    X = np.array(X)
    y = np.array(y)

    train_X, train_y, val_X, val_y = split_df_to_train_test(X, y)

    train_mean = np.mean(train_X)
    train_std = np.std(train_X)

    train_X = (train_X - train_mean) / train_std
    train_y = (train_y - train_mean) / train_std
    val_X = (val_X - train_mean) / train_std
    val_y = (val_y - train_mean) / train_std

    train_X = train_X.astype(np.double)
    train_y = train_y.astype(np.double)
    val_X = val_X.astype(np.double)
    val_y = val_y.astype(np.double)

    amount_of_features = train_X[0].shape[1]

    match player_data['position']:
        case 'GKP':
            n_hidden_layers = 2
            n_neurons = 256
            n_neurons_last_layer = 64
        case 'DEF':
            n_hidden_layers = 1
            n_neurons = 64
            n_neurons_last_layer = 64
        case 'MID':
            n_hidden_layers = 3
            n_neurons = 128
            n_neurons_last_layer = 128
        case 'FWD':
            n_hidden_layers = 2
            n_neurons = 64
            n_neurons_last_layer = 128

    es = EarlyStopping(monitor='val_loss', min_delta=0.005, mode="min", patience=5)
    lt = LimitTrainingTime(10)
    print('Training LSTM...')
    model = make_model(1, amount_of_features, n_neurons=n_neurons, n_hidden_layers=n_hidden_layers,
                       n_neurons_last_layer=n_neurons_last_layer)
    model.compile(optimizer="adam", loss='mse')
    model.fit(x=train_X, y=train_y, validation_data=(val_X, val_y), epochs=1000, verbose=0, callbacks=[es, lt])
    print('Making predictions...')
    predictions = []
    for game in pred_by['games']:
        if len(predictions) == 0:
            next_points = train_X[-1][0][0]
        else:
            next_points = predictions[-1]

        prediction = model.predict(np.array([[[next_points, game]]]))[0][0]
        predictions.append(prediction)

    predictions = (np.array(predictions) * train_std) + train_mean

    print('Done!')

    overall = sum(predictions)
    next_points = sum(predictions[:pred_by['next']])

    if overall / len(pred_by['games']) >= RETRY_POINT or overall / len(pred_by['games']) <= -RETRY_POINT:
        print("RETRY LSTM")
        print("train_X", train_X)
        print("overall / len(pred_by['games'])", overall / len(pred_by['games']))
        lstm_counter += 1
        return do_lstm(player_data, pred_by)

    lstm_counter = 0
    return [overall, next_points]
