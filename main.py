import csv
import json

from xlsxwriter.workbook import Workbook

from dataset import get_dataset
from game_information import TEAMS, get_team_info, CURRENT_SEASON, CURRENT_GAME_WEEK, CURRENT_SEASON_BEGINNING_ROUND, \
    SEASON_LENGTH, MIN_GAMES, MIN_SEASON_PPG, MIN_SEASON_GAME_PERCENTAGE
from ai import MAX_DIFF, do_arima, do_lstm

TEAM_WORTH = 98 + 2.5
FREE_TRANSFERS = 1
CURRENT_TEAM = {"Mark Flekken Flekken", "André Onana Onana",  # GKP
                "Micky van de Ven Van de Ven", "Pau Torres Pau", "Thiago Emiliano da Silva T.Silva",
                "Axel Disasi Disasi", "Kieran Trippier Trippier",  # DEF
                "Jarrod Bowen Bowen", "Bryan Mbeumo Mbeumo", "Raheem Sterling Sterling", "Dejan Kulusevski Kulusevski",
                "Moussa Diaby Diaby",  # MID
                "Erling Haaland Haaland", "Ollie Watkins Watkins", "Matheus Santos Carneiro Da Cunha Cunha"  # FWD
                }

PROCESS_ALL_PLAYERS = False
BUGGED_PLAYERS = []

PREDICT_BY_WEEKS = 5
RATIOS = {  # Last calibrated 11/3/2023
    'ARS': {'ARIMA': 0.404851335401092, 'LSTM': 0.525301001041839},
    'AVL': {'ARIMA': 0.5337763005735, 'LSTM': 0.63092183256713},
    'BOU': {'ARIMA': 0.352149478728991, 'LSTM': 0.330868435074501},
    'BRE': {'ARIMA': 0.571241693994131, 'LSTM': 0.558363654595077},
    'BHA': {'ARIMA': 0.424913067402086, 'LSTM': 0.450075436015669}, 'BUR': {'ARIMA': 0, 'LSTM': 0},
    'CHE': {'ARIMA': 0.507895290177915, 'LSTM': 0.492871785839962},
    'CRY': {'ARIMA': 0.574974240382309, 'LSTM': 0.566227644681761},
    'EVE': {'ARIMA': 0.468615312139941, 'LSTM': 0.416914909636597},
    'FUL': {'ARIMA': 0.482225008877753, 'LSTM': 0.430430126850038},
    'LIV': {'ARIMA': 0.429553002172322, 'LSTM': 0.399987703545445}, 'LUT': {'ARIMA': 0, 'LSTM': 0},
    'MCI': {'ARIMA': 0.457856934139545, 'LSTM': 0.330420706259275},
    'MUN': {'ARIMA': 0.37534796936456, 'LSTM': 0.360941791703677},
    'NEW': {'ARIMA': 0.543621565881507, 'LSTM': 0.506358470258735},
    'NFO': {'ARIMA': 0.468615193456151, 'LSTM': 0.416990653875408},
    'SHU': {'ARIMA': 0.297006784854757, 'LSTM': 0.719080832832509},
    'TOT': {'ARIMA': 0.568016430213264, 'LSTM': 0.492146224023965},
    'WHU': {'ARIMA': 0.40475931896671, 'LSTM': 0.504227911786362},
    'WOL': {'ARIMA': 0.647722802726038, 'LSTM': 0.737413821601548}}

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
    print(teams)

    with open(f"../Fantasy-Premier-League/data/{CURRENT_SEASON}/fixtures.csv") as fixtures_file:
        fixture_reader = csv.DictReader(fixtures_file)

        fixture_reader = [fixture for fixture in fixture_reader if
                          fixture['event'] != '' and CURRENT_GAME_WEEK <= float(fixture['event']) <= CURRENT_GAME_WEEK + PREDICT_BY_WEEKS - 1]

        for fixture in fixture_reader:
            predict_by[teams[int(fixture['team_h'])]['short_name']]['games'].append(int(fixture['team_h_difficulty']))
            predict_by[teams[int(fixture['team_a'])]['short_name']]['games'].append(int(fixture['team_a_difficulty']))

            if float(fixture['event']) == CURRENT_GAME_WEEK:
                predict_by[teams[int(fixture['team_h'])]['short_name']]['next'] += 1
                predict_by[teams[int(fixture['team_a'])]['short_name']]['next'] += 1

    make_training_set()


def make_training_set():
    done = 0
    total = len(points_data_set.keys())

    for _, player_data in points_data_set.items():
        print(player_data['id'], player_data['name'])
        done += 1

        if player_data['id'] in deleted_members or player_data['id'] in BUGGED_PLAYERS:
            print("Deleted")
            print(f"{(done / total) * 100}% done")
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
                SEASON_LENGTH if CURRENT_GAME_WEEK == 1 else CURRENT_GAME_WEEK - 1) * MIN_SEASON_GAME_PERCENTAGE or len(predict_by[player_data['team']]['games']) < 1 or total_games < 2) and not f"{player_data['first_name']} {player_data['last_name']} {player_data['name']}" in CURRENT_TEAM:
            print("Not min requirements")
            print(f"{(done / total) * 100}% done")
            continue

        if season_sum <= 0 or len(predict_by[player_data['team']]['games']) == 0:
            arima = [0, 0]
            lstm = [0, 0]
        else:
            try:
                arima = do_arima(ts, predict_by[player_data['team']])
                lstm = do_lstm(player_data, predict_by[player_data['team']])
            except:
                print("FAILED")
                print(f"{(done / total) * 100}% done")

                BUGGED_PLAYERS.append(player_data['id'])
                continue

        if arima[0] != 0 and lstm[0] != 0 and (arima[0] / lstm[0] > MAX_DIFF or lstm[0] / arima[0] > MAX_DIFF):
            print("ARIMA and LSTM is too different")
            print(f"{(done / total) * 100}% done")

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

        print(f"{(done / total) * 100}% done")

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

    sheet.add_table(f"A1:{ALPHABET[len(master_data_set[0]) - 1]}{len(master_data_set)}", {'data': data, 'columns': columns})

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
