import csv
import json
import os

from tqdm import tqdm
from xlsxwriter.workbook import Workbook

from ai import MAX_DIFF, do_arima, do_lstm, do_forest
from dataset import get_dataset, master_data_set as header
from game_information import TEAMS, get_team_info, CURRENT_SEASON, CURRENT_GAME_WEEK, CURRENT_SEASON_BEGINNING_ROUND, \
    SEASON_LENGTH, MIN_GAMES, MIN_SEASON_PPG, MIN_SEASON_GAME_PERCENTAGE, TEAM_WORTH, FREE_TRANSFERS, \
    PREDICT_BY_WEEKS, TRANSFER_COST, CHALLENGE_TEAM, CALIBRATE_BY, BUGGED_PLAYERS, PROCESS_ALL_PLAYERS
from solver import make_team, calibrate_player, TOTAL_PLAYERS
from calibrate import process_player_data

CURRENT_TEAM = {
    "André Onana Onana",
    "David Raya Martin Raya",

    "Gabriel dos Santos Magalhães Gabriel",
    "Andrew Robertson Robertson",
    "Diogo Dalot Teixeira Dalot",
    "William Saliba Saliba",
    "Pedro Porro Pedro Porro",

    "Mohamed Salah M.Salah",
    "Luis Díaz Luis Díaz",
    "Noni Madueke Madueke",
    "Bryan Mbeumo Mbeumo",
    "Harvey Barnes Barnes",

    "Jhon Durán Duran",
    "Raúl Jiménez Raúl",
    "Chris Wood Wood",
}

INJURIES = {
    "Alexander Isak Isak": 0.5,
    "Yoane Wissa Wissa": 0,
    "Jarrad Branthwaite Branthwaite": 0.75,
}

HIDDEN_COLUMNS = ['GKP', 'DEF', 'MID', 'FWD', *TEAMS, 'ID', 'ARIMA', 'LSTM', 'FOREST']
ALPHABET = [*"ABCDEFGHIJKLMNOPQRSTUVWXYZ"]
ID = header[0].index('ID')
PP = header[0].index('PP')
HEALTH = header[0].index('Health')
NEXT = header[0].index('NEXT')
PREV = header[0].index('PREV')
SELECTED = header[0].index('Selected')
FIRST_NAME = header[0].index('First Name')
SURNAME = header[0].index('Surname')
WEB_NAME = header[0].index('Web Name')

master_data_set = []
deleted_members = []
to_retry = []
points_data_set = {}
predict_by = {}


def init():
    for team in TEAMS:
        predict_by[team] = {'games': [], 'next': 0}

    for letter in [*"ABCDEFGHIJKLMNOPQRSTUVWXYZ"]:
        ALPHABET.append(f"A{letter}")

    global points_data_set, master_data_set
    points_data_set, master_data_set = get_dataset()

    get_predict_by()


def get_predict_by():
    teams = get_team_info()

    with open(f"../Fantasy-Premier-League/data/{CURRENT_SEASON}/fixtures.csv") as fixtures_file:
        fixture_reader = csv.DictReader(fixtures_file)

        fixture_reader = [fixture for fixture in fixture_reader if
                          fixture['event'] != '' and CURRENT_GAME_WEEK <= float(
                              fixture['event']) <= CURRENT_GAME_WEEK + PREDICT_BY_WEEKS - 1]

        for fixture in fixture_reader:
            predict_by[teams[int(fixture['team_h'])]['short_name']]['games'].append(int(fixture['team_h_difficulty']))
            predict_by[teams[int(fixture['team_a'])]['short_name']]['games'].append(int(fixture['team_a_difficulty']))

            if float(fixture['event']) == CURRENT_GAME_WEEK:
                predict_by[teams[int(fixture['team_h'])]['short_name']]['next'] += 1
                predict_by[teams[int(fixture['team_a'])]['short_name']]['next'] += 1

    make_training_set()


def make_training_set():
    global master_data_set

    found_previous = 0

    filename = f"./predictedData/{CURRENT_SEASON}/predictedData{CURRENT_GAME_WEEK}{"Challenge" if CHALLENGE_TEAM else ""}.json"
    if os.path.exists(filename):
        with open(filename, 'r') as file:
            master_data_set = json.load(file)

        print("Loaded predictions from file")

        for master in master_data_set:
            if len(master) != len(header[0]) or master == header[0]:
                continue

            player_name = f"{master[FIRST_NAME]} {master[SURNAME]} {master[WEB_NAME]}"
            if player_name in INJURIES:
                master[HEALTH] = INJURIES[player_name]
            else:
                master[HEALTH] = 1
            if player_name in CURRENT_TEAM:
                master[PREV] = 1
                found_previous += 1
            else:
                master[PREV] = 0

        if len(to_retry) == 0:
            make_prediction_file()
            return

    for _, player_data in tqdm(points_data_set.items()):
        if len(to_retry) > 0 and player_data['id'] not in to_retry:
            continue

        if player_data['id'] in deleted_members or player_data['id'] in BUGGED_PLAYERS:
            continue

        ts = []
        season_sum = 0
        num_games = 0
        total_games = 0

        player_name = f"{player_data['first_name']} {player_data['last_name']} {player_data['name']}"

        for dataset, data in player_data.items():
            if not dataset.startswith('GW'):
                continue

            total_games += 1
            ts.append(data['points'])

            round_num = int(dataset.replace("GW", ""))
            beginning_round = CURRENT_SEASON_BEGINNING_ROUND
            if CURRENT_GAME_WEEK <= CALIBRATE_BY:
                beginning_round = CURRENT_SEASON_BEGINNING_ROUND - SEASON_LENGTH - CURRENT_GAME_WEEK

            if round_num >= beginning_round:
                season_sum += data['points']
                num_games += 1

        if total_games < MIN_GAMES:
            continue

        if not PROCESS_ALL_PLAYERS and (
                total_games - CALIBRATE_BY < MIN_GAMES or season_sum < MIN_SEASON_PPG * num_games or num_games < (
                SEASON_LENGTH if CURRENT_GAME_WEEK <= CALIBRATE_BY else CURRENT_GAME_WEEK - 1) * MIN_SEASON_GAME_PERCENTAGE or
                len(predict_by[player_data['team']]['games']) < 1 or total_games < 2 or
                sum(ts[-PREDICT_BY_WEEKS:]) < PREDICT_BY_WEEKS * MIN_SEASON_PPG) and player_name not in CURRENT_TEAM:
            continue

        arima_ratio = 1/3
        lstm_ratio = 1/3
        forest_ratio = 1/3

        c_arima, c_lstm, c_forest, c_actual = process_player_data(player_data)
        if c_actual <= 0 and not PROCESS_ALL_PLAYERS:
            continue
        elif c_actual > 0:
            arima_ratio, lstm_ratio, forest_ratio = calibrate_player(c_arima, c_lstm, c_forest, c_actual)

        if season_sum <= 0 or len(predict_by[player_data['team']]['games']) == 0:
            arima_overall, arima_next = 0, 0
            lstm_overall, lstm_next = 0, 0
            forest_overall, forest_next = 0, 0
        else:
            try:
                if arima_ratio > 0:
                    arima_pred = do_arima(ts, predict_by[player_data['team']]['games'])
                    arima_overall = sum(arima_pred)
                    arima_next = sum(arima_pred[:predict_by[player_data['team']]['next']])
                else:
                    arima_overall, arima_next = 0, 0

                if lstm_ratio > 0:
                    lstm_pred = do_lstm(player_data, predict_by[player_data['team']]['games'])
                    lstm_overall = sum(lstm_pred)
                    lstm_next = sum(lstm_pred[:predict_by[player_data['team']]['next']])
                else:
                    lstm_overall, lstm_next = 0, 0

                if forest_ratio > 0:
                    forest_pred = do_forest(player_data, predict_by[player_data['team']]['games'])
                    forest_overall = sum(forest_pred)
                    forest_next = sum(forest_pred[:predict_by[player_data['team']]['next']])
                else:
                    forest_overall, forest_next = 0, 0
            except:
                print('ERROR', player_data['id'])
                BUGGED_PLAYERS.append(player_data['id'])
                continue

        if min(arima_overall, lstm_overall, forest_overall) > 0 and (max(arima_overall, lstm_overall, forest_overall) /
                                                                     min(arima_overall, lstm_overall, forest_overall)) > MAX_DIFF:
            print(player_data['id'], 'max diff', max(arima_overall, lstm_overall, forest_overall) /
                                                                     min(arima_overall, lstm_overall, forest_overall), arima_overall, lstm_overall, forest_overall)
            BUGGED_PLAYERS.append(player_data['id'])
            continue

        if len(predict_by[player_data['team']]['games']) == 0:
            p = 0
            next_p = 0
        else:
            p = (arima_overall * arima_ratio) + (lstm_overall * lstm_ratio) + (forest_overall * forest_ratio) / 3
            next_p = (arima_next * arima_ratio) + (lstm_next * lstm_ratio) + (forest_next * forest_ratio) / 3

        found = False
        for master in master_data_set:
            if master[ID] == player_data['id']:
                master.append(arima_overall)
                master.append(lstm_overall)
                master.append(forest_overall)
                master.append(p)
                master.append(next_p)
                if player_name in INJURIES:
                    master.append(INJURIES[player_name])
                else:
                    master.append(1)
                if player_name in CURRENT_TEAM:
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
        json.dump(master_data_set, dataset_file, ensure_ascii=False, indent=4)
        print("Wrote Predicted Data")

    if found_previous == TOTAL_PLAYERS:
        print("Found all previous players!")
    else:
        print(f"Found only {found_previous} out of {TOTAL_PLAYERS} previous players")

    make_prediction_file()


def make_prediction_file():
    global points_data_set, master_data_set

    workbook = Workbook(f"./Predictions/{CURRENT_SEASON}/Week {CURRENT_GAME_WEEK}{" Challenge" if CHALLENGE_TEAM else ""}.xlsx")
    sheet = workbook.add_worksheet()

    column_index = len(master_data_set[0]) + 1
    row_index = 1

    sheet.write_row(row_index, column_index, ["Total Points", "=SUMPRODUCT(Table1[Selected], Table1[PP])", "MAX"])

    row_index += 2

    sheet.write_row(row_index, column_index, ["Total Cost", "=SUMPRODUCT(Table1[Selected],Table1[Cost])", TEAM_WORTH])

    row_index += 2

    sheet.write_row(row_index, column_index, ["GKP", "=SUMPRODUCT(Table1[Selected],Table1[GKP])", 2])

    row_index += 1

    sheet.write_row(row_index, column_index, ["DEF", "=SUMPRODUCT(Table1[Selected],Table1[DEF])", 5])

    row_index += 1

    sheet.write_row(row_index, column_index, ["MID", "=SUMPRODUCT(Table1[Selected],Table1[MID])", 5])

    row_index += 1

    sheet.write_row(row_index, column_index, ["FWD", "=SUMPRODUCT(Table1[Selected],Table1[FWD])", 3])

    row_index += 2

    sheet.write_row(row_index, column_index, ["Transfers", "=SUMPRODUCT(Table1[Selected], -- (Table1[PREV] = 0))"])

    row_index += 1

    sheet.write_row(row_index, column_index, ["Free", FREE_TRANSFERS])

    row_index += 2

    sheet.write_row(row_index, column_index, ["Cost",
                                              f"=(({ALPHABET[column_index + 1]}{row_index - 2}-{ALPHABET[column_index + 1]}{row_index - 1})+ABS(({ALPHABET[column_index + 1]}{row_index - 2}-{ALPHABET[column_index + 1]}{row_index - 1})))/2*{TRANSFER_COST}"])

    row_index += 2

    sheet.write_row(row_index, column_index, ["Profit",
                                              f"={ALPHABET[column_index + 1]}{row_index - 13}-{ALPHABET[column_index + 1]}{row_index - 1}*{PREDICT_BY_WEEKS}"])

    row_index += 2

    for team_name in TEAMS:
        sheet.write_row(row_index, column_index, [team_name, f"=SUMPRODUCT(Table1[Selected],Table1[{team_name}])", 3])
        row_index += 1

    data = [player for player in master_data_set[1:] if len(player) == len(master_data_set[0])]

    if not CHALLENGE_TEAM:
        best_team = make_team(data)
    else:
        best_team = []

    found_selected = 0
    for player in data:
        player[PP] = f"={player[PP]}*{player[HEALTH]}"
        player[NEXT] = f"={player[NEXT]}*{player[HEALTH]}"

        if player in best_team:
            player[SELECTED] = 1
            found_selected += 1

    if found_selected == TOTAL_PLAYERS:
        print("Found all selected players!")
    else:
        print(f"Found only {found_selected} out of {TOTAL_PLAYERS} selected players")

    columns = list(map(lambda x: {'header': x}, master_data_set[0]))

    sheet.add_table(f"A1:{ALPHABET[len(master_data_set[0]) - 1]}{len(data) + 1}",
                    {'data': data, 'columns': columns})

    for column_name in HIDDEN_COLUMNS:
        hidden_column_index = master_data_set[0].index(column_name)
        sheet.set_column(hidden_column_index, hidden_column_index, None, None, {'hidden': 1})

    for bugged_player in BUGGED_PLAYERS:
        print("Did not include player with id", bugged_player)
        print(points_data_set[bugged_player])

    workbook.close()


if __name__ == "__main__":
    init()
