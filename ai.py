import warnings
import pandas as pd

import numpy as np
from pmdarima.arima import auto_arima
from tensorflow.keras.callbacks import EarlyStopping
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import GridSearchCV

from lstm_utils import split_df_to_train_test, make_model

warnings.filterwarnings("ignore", message="numpy.dtype size changed")
warnings.filterwarnings("ignore", message="numpy.ufunc size changed")
warnings.filterwarnings("ignore", message="RuntimeWarning: invalid value encountered in cast")

MAX_POINTS = 50
RETRY_POINT = 20
MAX_RETRIES = 5
MAX_DIFF = 5


def do_arima(ts, pred_by, arima_counter=0):
    if arima_counter == MAX_RETRIES:
        raise Exception("Too many ARIMA calls")

    if len(pred_by) == 0:
        return 0, 0

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
        return []

    if has_same_num is not False:
        return has_same_num, has_same_num

    try:
        arima = auto_arima(ts, seasonal=False, error_action="ignore")
        pred = arima.predict(len(pred_by))
    except Exception as e:
        print(e)
        return do_arima(ts, pred_by, arima_counter + 1)

    overall = sum(pred)

    if overall / len(pred_by) >= RETRY_POINT or overall / len(pred_by) <= -RETRY_POINT:
        return do_arima(ts, pred_by, arima_counter + 1)

    return pred


def do_lstm(player_data, pred_by, lstm_counter=0):
    if lstm_counter == MAX_RETRIES:
        raise Exception("Too many LSTM calls")

    if len(pred_by) == 0:
        return []

    x = []
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

        x.append([[last_points, gw_diff]])
        y.append([gw_points])

        last_points = gw_points

    x = np.array(x)
    y = np.array(y)

    train_x, train_y, val_x, val_y = split_df_to_train_test(x, y)

    amount_of_features = train_x[0].shape[1]

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
        case _:
            raise "Invalid position"

    try:
        es = EarlyStopping(monitor='val_loss', min_delta=0.005, mode="min", patience=5)
        model = make_model(1, amount_of_features, n_neurons=n_neurons, n_hidden_layers=n_hidden_layers,
                           n_neurons_last_layer=n_neurons_last_layer)
        model.compile(optimizer="adam", loss='mse')
        model.fit(x=train_x, y=train_y, validation_data=(val_x, val_y), epochs=1000, verbose=0, callbacks=[es])
        predictions = []
        for game in pred_by:
            if len(predictions) == 0:
                next_points = train_x[-1][0][0]
            else:
                next_points = predictions[-1]

            next_pred = np.array([[[next_points, game]]])
            next_pred = next_pred.astype(np.double)

            prediction = model.predict(next_pred, verbose=0)[0][0]
            predictions.append(prediction)

        predictions = np.array(predictions)
    except Exception as e:
        print(e)
        return do_lstm(player_data, pred_by, lstm_counter + 1)

    overall = sum(predictions)

    if overall / len(pred_by) >= RETRY_POINT or overall / len(pred_by) <= -RETRY_POINT:
        return do_lstm(player_data, pred_by, lstm_counter + 1)

    return predictions


def do_forest(player_data, pred_by, forest_counter=0):
    if forest_counter == MAX_RETRIES:
        raise Exception("Too many random forest calls")

    filtered_data = player_data.copy()
    for key, value in filtered_data.items():
        if not key.startswith("GW"):
            continue

        filtered_data[key] = value['points']

    df = pd.DataFrame(filtered_data, index=[0])
    df = df.drop(columns=['first_name', 'last_name', 'name', 'team', 'position'])

    gw_columns = [col for col in df.columns if col.startswith("GW")]
    df = df.melt(id_vars=['id'],
                 value_vars=gw_columns,
                 var_name='GW',
                 value_name='points')
    df.dropna(subset=['points'], inplace=True)
    df['GW'] = df['GW'].str.replace('GW', '').astype(int)
    df = df.sort_values(by=['id', 'GW'])
    df = df.drop(columns=['GW', 'id'])

    grid = {'max_depth': np.arange(1, 25, 4), 'n_estimators': np.arange(25, 100, 5)}

    rfr = RandomForestRegressor(max_features=1 / 3, n_jobs=1)
    rfr_cv = GridSearchCV(estimator=rfr, param_grid=grid, n_jobs=1)
    best_estimator = None
    pred = []

    for _ in pred_by:
        df['RecentFormAvg'] = df['points'].rolling(window=3, min_periods=1).mean().reset_index(0, drop=True)
        df['HistoricalPerformanceAvg'] = df['points'].expanding().mean().reset_index(0, drop=True)

        last_row = df.iloc[-1]
        x = df[:-1].drop(columns=['points'])
        y = df[:-1]['points']

        if best_estimator is None:
            rfr_cv.fit(x.to_numpy(), y)
            best_estimator = rfr_cv.best_estimator_

        pred.append(best_estimator.predict([last_row.drop('points')])[0])
        df.loc[len(df)] = {'points': pred[-1], 'RecentFormAvg': 0, 'HistoricalPerformanceAvg': 0}

    overall = sum(pred)

    if overall / len(pred_by) >= RETRY_POINT or overall / len(pred_by) <= -RETRY_POINT:
        return do_forest(player_data, pred_by, forest_counter + 1)

    return pred
