from ai import do_arima, do_lstm, do_forest, MAX_DIFF
from game_information import CURRENT_SEASON_BEGINNING_ROUND, CURRENT_GAME_WEEK, SEASON_LENGTH, MIN_GAMES, \
    MIN_SEASON_PPG, MIN_SEASON_GAME_PERCENTAGE, CALIBRATE_BY, BUGGED_PLAYERS, PROCESS_ALL_PLAYERS


def process_player_data(player_data):
    if player_data['id'] in BUGGED_PLAYERS:
        return -1, -1, -1, -1

    points_sum = 0
    num_games = 0
    total_games = 0

    gws = []

    for dataset, data in player_data.items():
        if not dataset.startswith('GW'):
            continue

        total_games += 1
        gws.append(data)

        round_num = int(dataset.replace('GW', ''))
        beginning_round = CURRENT_SEASON_BEGINNING_ROUND
        if CURRENT_GAME_WEEK <= CALIBRATE_BY:
            beginning_round = CURRENT_SEASON_BEGINNING_ROUND - SEASON_LENGTH - 1

        if round_num >= beginning_round:
            points_sum += data['points']
            num_games += 1

    if not PROCESS_ALL_PLAYERS and (
            total_games - CALIBRATE_BY < MIN_GAMES or points_sum < MIN_SEASON_PPG * num_games or num_games < (
            SEASON_LENGTH if CURRENT_GAME_WEEK <= CALIBRATE_BY else CURRENT_GAME_WEEK - 1) * MIN_SEASON_GAME_PERCENTAGE):
        return -1, -1, -1, -1

    pred_by = []
    training_player_data = {'id': player_data['id'], 'position': player_data['position'],
                            'first_name': player_data['first_name'], 'last_name': player_data['last_name'],
                            'name': player_data['name'], 'team': player_data['team']}

    for gw_num in range(0, len(gws) - CALIBRATE_BY + 1):
        training_player_data[f"GW{gw_num + 1}"] = gws[gw_num]

    actual_points = 0
    for gw in gws[len(gws) - CALIBRATE_BY + 1:]:
        pred_by.append(gw['diff'])
        actual_points += gw['points']

    if actual_points <= 0 or len(gws[:-CALIBRATE_BY]) <= CALIBRATE_BY:
        arima = 0
        lstm = 0
        forest = 0
    else:
        try:
            arima = sum(do_arima(list(map(lambda x: x['points'], gws[:-CALIBRATE_BY])), pred_by))
            lstm = sum(do_lstm(training_player_data, pred_by))
            forest = sum(do_forest(training_player_data, pred_by))
        except:
            print('AN ERROR HAPPENED')
            arima = 0
            lstm = 0
            forest = 0

        if arima != 0 and lstm != 0 and (arima / lstm > MAX_DIFF or lstm / arima > MAX_DIFF):
            arima = 0
            lstm = 0
            forest = 0

    return arima, lstm, forest, actual_points
