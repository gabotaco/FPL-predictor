import csv
import json
import os

from tqdm import tqdm
from xlsxwriter.workbook import Workbook

from ai import MAX_DIFF, do_arima, do_lstm, do_forest
from dataset import get_dataset
from game_information import (get_team_info, get_game_round, get_team_names, CURRENT_SEASON, CURRENT_GAME_WEEK,
                              SEASON_LENGTH, MIN_GAMES, MIN_SEASON_PPG, MIN_SEASON_GAME_PERCENTAGE, TEAM_WORTH,
                              FREE_TRANSFERS, PREDICT_BY_WEEKS, TRANSFER_COST, CHALLENGE_TEAM, CALIBRATE_BY,
                              BUGGED_PLAYERS, PROCESS_ALL_PLAYERS, USE_AVERAGE, TOTAL_PLAYERS, GKPs,
                              DEFs, MIDs, FWDs, MAX_PER_TEAM)
from solver import make_team_list, calibrate_player
from calibrate import process_player_data

CURRENT_TEAM = {
    "Jordan Pickford Pickford",
    "Matz Sels Sels",

    "James Tarkowski Tarkowski",
    "Vitalii Mykolenko Mykolenko",
    "Milos Kerkez Kerkez",
    "Lewis Hall Hall",
    "Ola Aina Aina",

    "Mohamed Salah M.Salah",
    "Jacob Murphy J.Murphy",
    "Amad Diallo Amad",
    "Son Heung-min Son",
    "Bruno Borges Fernandes B.Fernandes",

    "Matheus Santos Carneiro Da Cunha Cunha",
    "Yoane Wissa Wissa",
    "Alexander Isak Isak",
}
INJURIES = {
    "Micky van de Ven Van de Ven": 0,
    "Ashley Young Young": 0,
    "Bukayo Saka Saka": 0,
}
TO_RETRY = []
TO_IGNORE_MAX_WARNING = []

ALPHABET = [*"ABCDEFGHIJKLMNOPQRSTUVWXYZ", "AA", "AB", "AC", "AD", "AE", "AF", "AG", "AH", "AI", "AJ", "AK", "AL", "AM",
            "AN", "AO", "AP", "AQ", "AR", "AS", "AT", "AU", "AV", "AW", "AX", "AY", "AZ"]


def init(current_season, current_game_week, predict_by_weeks, challenge_team,
         calibrate_by, season_length, min_games, process_all_players, min_season_ppg,
         min_season_game_percentage, bugged_players, use_average, team_worth, free_transfers, transfer_cost,
         total_players, gkps, defs, mids, fwds, max_per_team):
    team_names = get_team_names(current_season)
    team_info = get_team_info(current_season)
    predict_by = get_predict_by(current_season, current_game_week, predict_by_weeks, team_info, team_names)
    points_data_set, incomplete_master_data_set = get_dataset(current_season)
    master_data_set, found_previous = make_predictions(current_season, current_game_week, challenge_team,
                                                       points_data_set, incomplete_master_data_set,
                                                       calibrate_by, season_length, min_games, process_all_players,
                                                       min_season_ppg, predict_by, predict_by_weeks,
                                                       min_season_game_percentage, bugged_players, use_average)
    if not challenge_team:
        if found_previous == total_players:
            print("Found all previous players!")
        else:
            print(f"Found only {found_previous} out of {total_players} previous players")

    make_prediction_file(current_season, current_game_week, challenge_team, master_data_set, team_worth, free_transfers,
                         transfer_cost, predict_by_weeks, team_names, points_data_set, total_players, bugged_players,
                         gkps, defs, mids, fwds, max_per_team)


def get_predict_by(current_season, current_game_week, predict_by_weeks, team_info, team_names):
    predict_by = {}
    for team in team_names:
        predict_by[team] = {'games': [], 'next': 0}

    with open(f"../Fantasy-Premier-League/data/{current_season}/fixtures.csv") as fixtures_file:
        fixture_reader = csv.DictReader(fixtures_file)

        fixture_reader = [fixture for fixture in fixture_reader if
                          fixture['event'] != '' and current_game_week <= float(
                              fixture['event']) <= current_game_week + predict_by_weeks - 1]

        for fixture in fixture_reader:
            predict_by[team_info[int(fixture['team_h'])]['short_name']]['games'].append(
                int(fixture['team_h_difficulty']))
            predict_by[team_info[int(fixture['team_a'])]['short_name']]['games'].append(
                int(fixture['team_a_difficulty']))

            if float(fixture['event']) == current_game_week:
                predict_by[team_info[int(fixture['team_h'])]['short_name']]['next'] += 1
                predict_by[team_info[int(fixture['team_a'])]['short_name']]['next'] += 1

    return predict_by


def load_prediction_file(filename, header):
    found_previous = 0
    health_index = header.index('Health')
    prev_index = header.index('PREV')
    first_name_index = header.index('First Name')
    surname_index = header.index('Surname')
    web_name_index = header.index('Web Name')

    with open(filename, 'r') as file:
        master_data_set = json.load(file)

    print("Loaded predictions from file")

    for master in master_data_set:
        if len(master) != len(header) or master == header:
            continue

        player_name = f"{master[first_name_index]} {master[surname_index]} {master[web_name_index]}"
        if player_name in INJURIES:
            master[health_index] = INJURIES[player_name]
        else:
            master[health_index] = 1

        if player_name in CURRENT_TEAM:
            master[prev_index] = 1
            found_previous += 1
        else:
            master[prev_index] = 0

    if len(TO_RETRY) == 0:
        return master_data_set, found_previous


def make_player_ts(player_data, current_season_beginning_round, current_game_week, calibrate_by, season_length,
                   min_games, process_all_players, min_season_ppg, min_season_game_percentage, predict_by,
                   predict_by_weeks):
    player_name = f"{player_data['first_name']} {player_data['last_name']} {player_data['name']}"
    ts = []
    season_sum = 0
    num_games = 0
    total_games = 0

    for dataset, data in player_data.items():
        if not dataset.startswith('GW'):
            continue

        total_games += 1
        ts.append(data['points'])

        round_num = int(dataset.replace("GW", ""))
        beginning_round = current_season_beginning_round
        if current_game_week <= calibrate_by:
            beginning_round = current_season_beginning_round - season_length - current_game_week

        if round_num >= beginning_round:
            season_sum += data['points']
            num_games += 1

    if total_games < min_games:
        return None

    if not process_all_players and (
            total_games - calibrate_by < min_games or season_sum < min_season_ppg * num_games or num_games < (
            season_length if current_game_week <= calibrate_by else current_game_week - 1) *
            min_season_game_percentage or len(predict_by[player_data['team']]['games']) < 1 or total_games < 2 or
            sum(ts[-predict_by_weeks:]) < predict_by_weeks * min_season_ppg) and player_name not in CURRENT_TEAM:
        return None
    if season_sum <= 0 or len(predict_by[player_data['team']]['games']) == 0:
        return None

    return ts


def make_predictions(current_season, current_game_week, challenge_team, points_data_set, incomplete_master_data_set,
                     calibrate_by, season_length, min_games, process_all_players, min_season_ppg, predict_by,
                     predict_by_weeks, min_season_game_percentage, bugged_players, use_average):
    filename = (f"./predictedData/{current_season}/predictedData{current_game_week}"
                f"{"Challenge" if challenge_team else ""}.json")
    header = incomplete_master_data_set[0]
    current_season_beginning_round = get_game_round(current_season)

    if os.path.exists(filename):
        return load_prediction_file(filename, header)

    found_previous = 0
    id_index = header.index('ID')

    for _, player_data in tqdm(points_data_set.items()):
        if len(TO_RETRY) > 0 and player_data['id'] not in TO_RETRY:
            continue

        if player_data['id'] in bugged_players:
            continue

        player_name = f"{player_data['first_name']} {player_data['last_name']} {player_data['name']}"
        ts = make_player_ts(player_data, current_season_beginning_round, current_game_week, calibrate_by, season_length,
                            min_games, process_all_players, min_season_ppg, min_season_game_percentage, predict_by,
                            predict_by_weeks)
        if ts is None:
            continue

        arima_ratio = 1 / 3
        lstm_ratio = 1 / 3
        forest_ratio = 1 / 3

        c_arima, c_lstm, c_forest, c_actual, average_points = process_player_data(player_data,
                                                                                  current_season_beginning_round,
                                                                                  current_game_week, season_length,
                                                                                  min_games, min_season_ppg,
                                                                                  min_season_game_percentage,
                                                                                  calibrate_by, bugged_players,
                                                                                  process_all_players)
        if c_actual <= 0 and not process_all_players:
            continue
        elif c_actual > 0:
            arima_ratio, lstm_ratio, forest_ratio = calibrate_player(c_arima, c_lstm, c_forest, c_actual)

        pred_by = predict_by[player_data['team']]['games'][
                  :predict_by[player_data['team']]['next']] if use_average else predict_by[player_data['team']][
            'games']
        average_overall = average_points * len(predict_by[player_data['team']]['games'])
        try:
            if arima_ratio > 0:
                arima_pred = do_arima(ts, pred_by)
                arima_overall = average_overall if use_average else sum(arima_pred)
                arima_next = sum(arima_pred[:predict_by[player_data['team']]['next']])
            else:
                arima_overall, arima_next = 0, 0

            if lstm_ratio > 0:
                lstm_pred = do_lstm(player_data, pred_by)
                lstm_overall = average_overall if use_average else sum(lstm_pred)
                lstm_next = sum(lstm_pred[:predict_by[player_data['team']]['next']])
            else:
                lstm_overall, lstm_next = 0, 0

            if forest_ratio > 0:
                forest_pred = do_forest(player_data, pred_by)
                forest_overall = average_overall if use_average else sum(forest_pred)
                forest_next = sum(forest_pred[:predict_by[player_data['team']]['next']])
            else:
                forest_overall, forest_next = 0, 0
        except Exception as e:
            print('ERROR', player_data['id'])
            print(e)
            bugged_players.append(player_data['id'])
            continue

        if (player_data['id'] not in TO_IGNORE_MAX_WARNING and min(arima_overall, lstm_overall, forest_overall) > 0 and
                (max(arima_overall, lstm_overall, forest_overall) / min(arima_overall, lstm_overall,
                                                                        forest_overall)) > MAX_DIFF):
            print(player_data['id'], 'max diff', max(arima_overall, lstm_overall, forest_overall) /
                  min(arima_overall, lstm_overall, forest_overall), arima_overall, lstm_overall, forest_overall)
            bugged_players.append(player_data['id'])
            continue

        if len(predict_by[player_data['team']]['games']) == 0:
            p = 0
            next_p = 0
        else:
            p = (arima_overall * arima_ratio) + (lstm_overall * lstm_ratio) + (forest_overall * forest_ratio) / 3
            next_p = (arima_next * arima_ratio) + (lstm_next * lstm_ratio) + (forest_next * forest_ratio) / 3

        found = False
        for master in incomplete_master_data_set:
            if master[id_index] == player_data['id']:
                master.append(arima_overall)
                master.append(lstm_overall)
                master.append(forest_overall)
                master.append(p)
                master.append(next_p)
                if player_name in INJURIES:
                    master.append(INJURIES[player_name])
                else:
                    master.append(1)
                if player_name in CURRENT_TEAM and not challenge_team:
                    master.append(1)
                    found_previous += 1
                else:
                    master.append(0)
                master.append(0)
                found = True
                break

        if not found:
            raise Exception(f"Couldn't find {player_data.id}")

    with open(filename, 'w') as dataset_file:
        json.dump(incomplete_master_data_set, dataset_file, ensure_ascii=False, indent=4)
        print("Wrote Predicted Data")

    return incomplete_master_data_set, found_previous


def make_prediction_file(current_season, current_game_week, challenge_team, master_data_set, team_worth,
                         free_transfers, transfer_cost, predict_by_weeks, team_names, points_data_set, total_players,
                         bugged_players, gkps, defs, mids, fwds, max_per_team):
    hidden_columns = ['GKP', 'DEF', 'MID', 'FWD', *team_names, 'ID', 'ARIMA', 'LSTM', 'FOREST']
    if challenge_team:
        hidden_columns.append("PREV")
    header = master_data_set[0]
    pp_index = header.index("PP")
    health_index = header.index("Health")
    next_index = header.index("NEXT")
    first_name_index = header.index("First Name")
    surname_index = header.index("Surname")
    selected_index = header.index("Selected")

    workbook = Workbook(
        f"./Predictions/{current_season}/Week {current_game_week}{" Challenge" if challenge_team else ""}.xlsx")
    sheet = workbook.add_worksheet()

    column_index = len(header) + 1
    row_index = 1

    points_column = 'PP' if predict_by_weeks > 1 else 'NEXT'
    sheet.write_row(row_index, column_index, ["Total Points", f"=SUMPRODUCT(Table1[Selected], Table1[{points_column}])",
                                              "MAX"])

    row_index += 2

    if team_worth is not None:
        sheet.write_row(row_index, column_index, ["Total Cost", "=SUMPRODUCT(Table1[Selected],Table1[Cost])",
                                                  team_worth])

        row_index += 2

    min_gkp, max_gkp = gkps
    sheet.write_row(row_index, column_index, ["GKP", min_gkp, "=SUMPRODUCT(Table1[Selected],Table1[GKP])", max_gkp])

    row_index += 1

    min_def, max_def = defs
    sheet.write_row(row_index, column_index, ["DEF", min_def, "=SUMPRODUCT(Table1[Selected],Table1[DEF])", max_def])

    row_index += 1

    min_mid, max_mid = mids
    sheet.write_row(row_index, column_index, ["MID", min_mid, "=SUMPRODUCT(Table1[Selected],Table1[MID])", max_mid])

    row_index += 1

    min_fwd, max_fwd = fwds
    sheet.write_row(row_index, column_index, ["FWD", min_fwd, "=SUMPRODUCT(Table1[Selected],Table1[FWD])", max_fwd])

    row_index += 1

    sheet.write_row(row_index, column_index, ["TOTAL", total_players, "=SUM(SUMPRODUCT(Table1[Selected],Table1[GKP]), "
                                                                      "SUMPRODUCT(Table1[Selected],Table1[DEF]), "
                                                                      "SUMPRODUCT(Table1[Selected],Table1[MID]), "
                                                                      "SUMPRODUCT(Table1[Selected],Table1[FWD]))",
                                              total_players])

    row_index += 2

    if transfer_cost != 0 and transfer_cost is not None:

        sheet.write_row(row_index, column_index, ["Transfers", "=SUMPRODUCT(Table1[Selected], -- (Table1[PREV] = 0))"])

        row_index += 1

        sheet.write_row(row_index, column_index, ["Free", free_transfers])

        row_index += 2

        sheet.write_row(row_index, column_index, ["Cost",
                                                  f"=(({ALPHABET[column_index + 1]}{row_index - 2}-"
                                                  f"{ALPHABET[column_index + 1]}{row_index - 1})+ABS(("
                                                  f"{ALPHABET[column_index + 1]}{row_index - 2}-"
                                                  f"{ALPHABET[column_index + 1]}{row_index - 1})))/2*{transfer_cost}"])

        row_index += 2

        sheet.write_row(row_index, column_index, ["Profit",
                                                  f"={ALPHABET[column_index + 1]}{row_index - 13}-"
                                                  f"{ALPHABET[column_index + 1]}{row_index - 1}*{predict_by_weeks}"])

        row_index += 2

    if max_per_team is not None and max_per_team < total_players:
        for team_name in team_names:
            sheet.write_row(row_index, column_index, [team_name, f"=SUMPRODUCT(Table1[Selected],Table1[{team_name}])",
                                                      max_per_team])
            row_index += 1

    data = [player for player in master_data_set[1:] if len(player) == len(header)]

    best_team = make_team_list(data, team_names, header, predict_by_weeks, transfer_cost, free_transfers,
                               team_worth, gkps, defs, mids, fwds, total_players, max_per_team)

    found_selected = 0
    for player in data:
        player[pp_index] = f"={player[pp_index]}*{player[health_index]}"
        player[next_index] = f"={player[next_index]}*{player[health_index]}"

        if f"{player[first_name_index]} {player[surname_index]}" in best_team:
            player[selected_index] = 1
            found_selected += 1

    if found_selected == total_players:
        print("Found all selected players!")
    else:
        print(f"Found only {found_selected} out of {total_players} selected players")

    columns = list(map(lambda x: {'header': x}, header))

    sheet.add_table(f"A1:{ALPHABET[len(header) - 1]}{len(data) + 1}",
                    {'data': data, 'columns': columns})

    for column_name in hidden_columns:
        hidden_column_index = header.index(column_name)
        sheet.set_column(hidden_column_index, hidden_column_index, None, None, {'hidden': 1})

    for bugged_player in bugged_players:
        print("Did not include player with id", bugged_player)
        print(points_data_set[bugged_player])

    workbook.close()


if __name__ == "__main__":
    init(CURRENT_SEASON, CURRENT_GAME_WEEK, PREDICT_BY_WEEKS, CHALLENGE_TEAM, CALIBRATE_BY,
         SEASON_LENGTH, MIN_GAMES, PROCESS_ALL_PLAYERS, MIN_SEASON_PPG, MIN_SEASON_GAME_PERCENTAGE, BUGGED_PLAYERS,
         USE_AVERAGE, TEAM_WORTH, FREE_TRANSFERS, TRANSFER_COST, TOTAL_PLAYERS, GKPs, DEFs, MIDs, FWDs, MAX_PER_TEAM)
