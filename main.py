import csv
import json

from tqdm import tqdm
from xlsxwriter.workbook import Workbook

from ai import MAX_DIFF, do_arima, do_lstm
from dataset import get_dataset
from game_information import TEAMS, get_team_info, CURRENT_SEASON, CURRENT_GAME_WEEK, CURRENT_SEASON_BEGINNING_ROUND, \
    SEASON_LENGTH, MIN_GAMES, MIN_SEASON_PPG, MIN_SEASON_GAME_PERCENTAGE

TEAM_WORTH = 99.5 + 1.6
FREE_TRANSFERS = 2
CURRENT_TEAM = {"Guglielmo Vicario Vicario", "Nick Pope Pope",  # GKP
                "Kristoffer Ajer Ajer", "Thiago Emiliano da Silva T.Silva", "Pau Torres Pau",
                "Kieran Trippier Trippier", "Axel Disasi Disasi",  # DEF
                "Jarrod Bowen Bowen", "Bryan Mbeumo Mbeumo", "Raheem Sterling Sterling", "Dejan Kulusevski Kulusevski",
                "Moussa Diaby Diaby",  # MID
                "Erling Haaland Haaland", "Gabriel Fernando de Jesus G.Jesus", "Matheus Santos Carneiro Da Cunha Cunha"  # FWD
                }

PROCESS_ALL_PLAYERS = False
BUGGED_PLAYERS = []

PREDICT_BY_WEEKS = 5
RATIOS = {  # Last calibrated 12/1/2023
    'ARS': {'ARIMA': 0.567339206445579, 'LSTM': 0.539145600094256},
    'AVL': {'ARIMA': 0.61316742044139, 'LSTM': 0.477002251633238},
    'BOU': {'ARIMA': 0.563348059202893, 'LSTM': 0.556449236940034},
    'BRE': {'ARIMA': 0.536948015714704, 'LSTM': 0.528103331261309},
    'BHA': {'ARIMA': 0.548920728259573, 'LSTM': 0.51513266132758},
    'BUR': {'ARIMA': 0.534692568525508, 'LSTM': 0.576905145547787},
    'CHE': {'ARIMA': 0.540320878831954, 'LSTM': 0.69081635062584},
    'CRY': {'ARIMA': 0.533894223622947, 'LSTM': 0.553653296491337},
    'EVE': {'ARIMA': 0.486107346458598, 'LSTM': 0.53259431663548},
    'FUL': {'ARIMA': 0.473155472316396, 'LSTM': 0.475290473182968},
    'LIV': {'ARIMA': 0.490922569495543, 'LSTM': 0.453341250571226}, 'LUT': {'ARIMA': 0, 'LSTM': 0},
    'MCI': {'ARIMA': 0.551340385811595, 'LSTM': 0.525774455311935},
    'MUN': {'ARIMA': 0.49484866384507, 'LSTM': 0.495415674413912},
    'NEW': {'ARIMA': 0.650733873407808, 'LSTM': 0.622489167751137},
    'NFO': {'ARIMA': 0.558741806810752, 'LSTM': 0.515433501703618},
    'SHU': {'ARIMA': 0.445502834320701, 'LSTM': 0.599573948435389},
    'TOT': {'ARIMA': 0.518924551030172, 'LSTM': 0.431980218357778},
    'WHU': {'ARIMA': 0.480381681468999, 'LSTM': 0.492119919222618},
    'WOL': {'ARIMA': 0.723905809351621, 'LSTM': 0.777843054500015}}

HIDDEN_COLUMNS = ['GKP', 'DEF', 'MID', 'FWD', *TEAMS, 'ID', 'ARIMA', 'LSTM']

master_data_set = []
deleted_members = []
points_data_set = {}
predict_by = {}
ALPHABET = [*"ABCDEFGHIJKLMNOPQRSTUVWXYZ"]


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
    for _, player_data in tqdm(points_data_set.items()):
        if player_data['id'] in deleted_members or player_data['id'] in BUGGED_PLAYERS:
            continue

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
            beginning_round = CURRENT_SEASON_BEGINNING_ROUND
            if CURRENT_GAME_WEEK == 1:
                beginning_round = CURRENT_SEASON_BEGINNING_ROUND - SEASON_LENGTH - CURRENT_GAME_WEEK

            if round_num >= beginning_round:
                season_sum += data['points']
                num_games += 1

        if not PROCESS_ALL_PLAYERS and (
                total_games < MIN_GAMES or season_sum < MIN_SEASON_PPG * num_games or num_games < (
                SEASON_LENGTH if CURRENT_GAME_WEEK == 1 else CURRENT_GAME_WEEK - 1) * MIN_SEASON_GAME_PERCENTAGE or len(
            predict_by[player_data['team']][
                'games']) < 1 or total_games < 2) and not f"{player_data['first_name']} {player_data['last_name']} {player_data['name']}" in CURRENT_TEAM:
            continue

        if season_sum <= 0 or len(predict_by[player_data['team']]['games']) == 0:
            arima = [0, 0]
            lstm = [0, 0]
        else:
            try:
                arima = do_arima(ts, predict_by[player_data['team']])
                lstm = do_lstm(player_data, predict_by[player_data['team']])
            except:
                BUGGED_PLAYERS.append(player_data['id'])
                continue

        if arima[0] != 0 and lstm[0] != 0 and (arima[0] / lstm[0] > MAX_DIFF or lstm[0] / arima[0] > MAX_DIFF):
            BUGGED_PLAYERS.append(player_data['id'])
            continue

        if len(predict_by[player_data['team']]['games']) == 0:
            p = 0
            next_p = 0
        else:
            arima_ratio = RATIOS[player_data['team']]['ARIMA']
            lstm_ratio = RATIOS[player_data['team']]['LSTM']

            p = (arima[0] * arima_ratio) + (lstm[0] * lstm_ratio)
            next_p = (arima[1] * arima_ratio) + (lstm[1] * lstm_ratio)

        found = False
        for master in master_data_set:
            if master[master_data_set[0].index('ID')] == player_data['id']:
                master.append(arima[0])
                master.append(lstm[0])
                master.append(p)
                master.append(next_p)
                master.append(0)
                master.append(0)
                found = True
                break

        if not found:
            raise Exception(f"Couldn't find {player_data.id}")

    with open(f"./predictedData/{CURRENT_SEASON}/predictedData{CURRENT_GAME_WEEK}.json", 'w') as dataset_file:
        json.dump(master_data_set, dataset_file, ensure_ascii=False, indent=4)
        print("Wrote Predicted Data")

    make_prediction_file()


def make_prediction_file():
    global points_data_set

    workbook = Workbook(f"./Predictions/{CURRENT_SEASON}/Week {CURRENT_GAME_WEEK}.xlsx")
    sheet = workbook.add_worksheet()

    column_index = len(master_data_set[0]) + 1
    row_index = 1

    sheet.write_row(row_index, column_index, ["Total Points", "=SUMPRODUCT(Table1[Selected], Table1[PPG])", "MAX"])

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
                                              f"=(({ALPHABET[column_index + 1]}{row_index - 2}-{ALPHABET[column_index + 1]}{row_index - 1})+ABS(({ALPHABET[column_index + 1]}{row_index - 2}-{ALPHABET[column_index + 1]}{row_index - 1})))/2*4"])

    row_index += 2

    sheet.write_row(row_index, column_index, ["Profit",
                                              f"={ALPHABET[column_index + 1]}{row_index - 13}-{ALPHABET[column_index + 1]}{row_index - 1}*{PREDICT_BY_WEEKS}"])

    row_index += 2

    for team_name in TEAMS:
        sheet.write_row(row_index, column_index, [team_name, f"=SUMPRODUCT(Table1[Selected],Table1[{team_name}])", 3])
        row_index += 1

    found_previous = 0

    data = [player for player in master_data_set[1:] if len(player) == len(master_data_set[0])]

    for player in data:
        if f"{player[master_data_set[0].index('First Name')]} {player[master_data_set[0].index('Surname')]} {player[master_data_set[0].index('Web Name')]}" in CURRENT_TEAM:
            player[master_data_set[0].index('PREV')] = 1
            found_previous += 1

    columns = list(map(lambda x: {'header': x}, master_data_set[0]))

    sheet.add_table(f"A1:{ALPHABET[len(master_data_set[0]) - 1]}{len(master_data_set)}",
                    {'data': data, 'columns': columns})

    for column_name in HIDDEN_COLUMNS:
        hidden_column_index = master_data_set[0].index(column_name)
        sheet.set_column(hidden_column_index, hidden_column_index, None, None, {'hidden': 1})

    if found_previous == 15:
        print("Found all previous players!")
    else:
        print(f"Found only {found_previous} out of 15 previous players")

    for bugged_player in BUGGED_PLAYERS:
        print("Did not include player with id", bugged_player)
        print(points_data_set[bugged_player])

    workbook.close()


if __name__ == "__main__":
    init()
