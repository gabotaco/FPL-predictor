from ai import do_arima, do_lstm, do_forest


def process_player_data(player_data, current_season_beginning_round, current_game_week, season_length, min_games,
                        min_season_ppg, min_season_game_percentage, calibrate_by, bugged_players, process_all_players,
                        max_diff):
    if player_data['id'] in bugged_players:
        return -1, -1, -1, -1, 0

    points_sum = 0
    num_games = 0
    total_games = 0

    gws = []

    for dataset, data in player_data.items():
        if not dataset.startswith('GW'):
            continue

        round_num = int(dataset.replace("GW", ""))
        if round_num >= current_season_beginning_round + current_game_week - 1:
            continue

        total_games += 1
        gws.append(data)

        beginning_round = current_season_beginning_round
        if current_game_week <= calibrate_by:
            beginning_round = current_season_beginning_round - season_length - 1

        if round_num >= beginning_round:
            points_sum += data['points']
            num_games += 1

    if not process_all_players and (
            total_games - calibrate_by < min_games or points_sum < min_season_ppg * num_games or num_games < (
            season_length if current_game_week <= calibrate_by else current_game_week - 1) *
            min_season_game_percentage):
        return -1, -1, -1, -1, 0

    pred_by = []
    training_player_data = {'id': player_data['id'], 'position': player_data['position'],
                            'first_name': player_data['first_name'], 'last_name': player_data['last_name'],
                            'name': player_data['name'], 'team': player_data['team']}

    for gw_num in range(0, len(gws) - calibrate_by + 1):
        training_player_data[f"GW{gw_num + 1}"] = gws[gw_num]

    actual_points = 0
    for gw in gws[len(gws) - calibrate_by + 1:]:
        pred_by.append(gw['diff'])
        actual_points += gw['points']

    if actual_points <= 0 or len(gws[:-calibrate_by]) <= calibrate_by:
        arima = 0
        lstm = 0
        forest = 0
    else:
        try:
            arima = sum(do_arima(list(map(lambda x: x['points'], gws[:-calibrate_by])), pred_by))
            lstm = sum(do_lstm(training_player_data, pred_by))
            forest = sum(do_forest(training_player_data, pred_by))
        except Exception as e:
            print(e)
            print('AN ERROR HAPPENED')
            arima = 0
            lstm = 0
            forest = 0

        if arima != 0 and lstm != 0 and (arima / lstm > max_diff or lstm / arima > max_diff):
            arima = 0
            lstm = 0
            forest = 0

    return arima, lstm, forest, actual_points, actual_points / len(pred_by)
