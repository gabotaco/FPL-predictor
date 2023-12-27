import csv
import json
import os

from tqdm import tqdm
from xlsxwriter.workbook import Workbook

from ai import MAX_DIFF, do_arima, do_lstm
from dataset import get_dataset, master_data_set as header
from game_information import TEAMS, get_team_info, CURRENT_SEASON, CURRENT_GAME_WEEK, CURRENT_SEASON_BEGINNING_ROUND, \
    SEASON_LENGTH, MIN_GAMES, MIN_SEASON_PPG, MIN_SEASON_GAME_PERCENTAGE, TEAM_WORTH, FREE_TRANSFERS, \
    PREDICT_BY_WEEKS, TRANSFER_COST
from solver import make_team

CURRENT_TEAM = {"Guglielmo Vicario Vicario", "Norberto Murara Neto Neto",  # GKP
                "William Saliba Saliba", "Thiago Emiliano da Silva T.Silva", "Pau Torres Pau",
                "Trent Alexander-Arnold Alexander-Arnold", "Axel Disasi Disasi",  # DEF
                "Jarrod Bowen Bowen", "Anthony Gordon Gordon", "Raheem Sterling Sterling", "Dejan Kulusevski Kulusevski",
                "Moussa Diaby Diaby",  # MID
                "Erling Haaland Haaland", "Gabriel Fernando de Jesus G.Jesus", "Matheus Santos Carneiro Da Cunha Cunha"
                # FWD
                }

INJURIES = {
    "Raheem Sterling Sterling": (PREDICT_BY_WEEKS - 1)/PREDICT_BY_WEEKS,
    "Erling Haaland Haaland": 0.5,
    "Pau Torres Pau": 0.5,
    "Serge Aurier Aurier": 0.5
}

RATIOS = {  # Last calibrated 12/25/2023
    'ARS': {'ARIMA': 0.50553623655838, 'LSTM': 0.454345051004099},
    'AVL': {'ARIMA': 0.564641648682363, 'LSTM': 0.527483353195708},
    'BOU': {'ARIMA': 0.638059753084607, 'LSTM': 0.644833776984598},
    'BRE': {'ARIMA': 0.566676989047784, 'LSTM': 0.578795017463655},
    'BHA': {'ARIMA': 0.494772823273238, 'LSTM': 0.474857204009663},
    'BUR': {'ARIMA': 0.539114207104266, 'LSTM': 0.594334221046895},
    'CHE': {'ARIMA': 0.532672846260096, 'LSTM': 0.492063759425385},
    'CRY': {'ARIMA': 0.495909345857948, 'LSTM': 0.501211903709602},
    'EVE': {'ARIMA': 0.650140579987114, 'LSTM': 0.674000890152615},
    'FUL': {'ARIMA': 0.51315899132696, 'LSTM': 0.563898749896529},
    'LIV': {'ARIMA': 0.546434991971343, 'LSTM': 0.511753158173029},
    'LUT': {'ARIMA': 0.705556634105279, 'LSTM': 0.76230898101798},
    'MCI': {'ARIMA': 0.46634960088672, 'LSTM': 0.394751272555966},
    'MUN': {'ARIMA': 0.500722939580096, 'LSTM': 0.501046243826412},
    'NEW': {'ARIMA': 0.579873687250869, 'LSTM': 0.551905385559895},
    'NFO': {'ARIMA': 0.639384593553014, 'LSTM': 0.633975523245651},
    'SHU': {'ARIMA': 0.475989081159247, 'LSTM': 0.601000600735684},
    'TOT': {'ARIMA': 0.555900713040891, 'LSTM': 0.545324532147467},
    'WHU': {'ARIMA': 0.539361405541248, 'LSTM': 0.510878217734147},
    'WOL': {'ARIMA': 0.614508560562473, 'LSTM': 0.523143166742825}}

PROCESS_ALL_PLAYERS = False
BUGGED_PLAYERS = []
HIDDEN_COLUMNS = ['GKP', 'DEF', 'MID', 'FWD', *TEAMS, 'ID', 'ARIMA', 'LSTM']
ALPHABET = [*"ABCDEFGHIJKLMNOPQRSTUVWXYZ"]
ID = header[0].index('ID')
PP = header[0].index('PP')
HEALTH = header[0].index('Health')
NEXT = header[0].index('NEXT')
SELECTED = header[0].index('Selected')

master_data_set = []
deleted_members = []
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

    filename = f"./predictedData/{CURRENT_SEASON}/predictedData{CURRENT_GAME_WEEK}.json"
    if os.path.exists(filename):
        with open(filename, 'r') as file:
            master_data_set = json.load(file)

        print("Loaded predictions from file")
        make_prediction_file()
        return

    found_previous = 0

    for _, player_data in tqdm(points_data_set.items()):
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
            if CURRENT_GAME_WEEK == 1:
                beginning_round = CURRENT_SEASON_BEGINNING_ROUND - SEASON_LENGTH - CURRENT_GAME_WEEK

            if round_num >= beginning_round:
                season_sum += data['points']
                num_games += 1

        if not PROCESS_ALL_PLAYERS and (
                total_games < MIN_GAMES or season_sum < MIN_SEASON_PPG * num_games or num_games < (
                SEASON_LENGTH if CURRENT_GAME_WEEK == 1 else CURRENT_GAME_WEEK - 1) * MIN_SEASON_GAME_PERCENTAGE or len(
            predict_by[player_data['team']][
                'games']) < 1 or total_games < 2) and player_name not in CURRENT_TEAM:
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
            if master[ID] == player_data['id']:
                master.append(arima[0])
                master.append(lstm[0])
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

    if found_previous == 15:
        print("Found all previous players!")
    else:
        print(f"Found only {found_previous} out of 15 previous players")

    make_prediction_file()


def make_prediction_file():
    global points_data_set, master_data_set

    workbook = Workbook(f"./Predictions/{CURRENT_SEASON}/Week {CURRENT_GAME_WEEK}.xlsx")
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

    best_team = make_team(data)

    found_selected = 0
    for player in data:
        player[PP] = f"={player[PP]}*{player[HEALTH]}"
        player[NEXT] = f"={player[NEXT]}*{player[HEALTH]}"

        if player in best_team:
            player[SELECTED] = 1
            found_selected += 1

    if found_selected == 15:
        print("Found all selected players!")
    else:
        print(f"Found only {found_selected} out of 15 selected players")

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
