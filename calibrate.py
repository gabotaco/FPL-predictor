from xlsxwriter.workbook import Workbook
from tqdm import tqdm

from ai import do_arima, do_lstm, MAX_DIFF
from dataset import get_dataset
from game_information import TEAMS, CURRENT_SEASON_BEGINNING_ROUND, CURRENT_GAME_WEEK, SEASON_LENGTH, MIN_GAMES, \
    MIN_SEASON_PPG, MIN_SEASON_GAME_PERCENTAGE, CURRENT_SEASON
from solver import make_calibration

CALIBRATE_BY = 10

BUGGED_PLAYERS = []

HEADERS = ["Name", "ARIMAPP", "LSTMPP", "PP", "AP", "DIFF"]
ALPHABET = [*"ABCDEFGHIJKLMNOPQRSTUVWXYZ"]

PROCESS_ALL_PLAYERS = False

players = {}
points_data_set = {}


def init():
    global players, points_data_set
    for team in TEAMS:
        players[team] = []

    (points_data_set, _) = get_dataset()
    get_basic_players_teams()


def get_basic_players_teams():
    global players
    for player_data in points_data_set.values():
        players[player_data['team']].append(player_data)

    get_player_predictions()


def get_player_predictions():
    global players

    for team in tqdm(TEAMS, desc="Teams", bar_format="{l_bar}{bar}| {remaining}"):
        for index, player_data in enumerate(
                tqdm(players[team], desc=f"{team} players", bar_format="{l_bar}{bar}| {remaining}")):
            if player_data['id'] in BUGGED_PLAYERS:
                continue

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
                if CURRENT_GAME_WEEK == 1:
                    beginning_round = CURRENT_SEASON_BEGINNING_ROUND - SEASON_LENGTH - 1

                if round_num >= beginning_round:
                    points_sum += data['points']
                    num_games += 1

            if not PROCESS_ALL_PLAYERS and (
                    total_games - CALIBRATE_BY < MIN_GAMES or points_sum < MIN_SEASON_PPG * num_games or num_games < (
                    SEASON_LENGTH if CURRENT_GAME_WEEK == 1 else CURRENT_GAME_WEEK - 1) * MIN_SEASON_GAME_PERCENTAGE or
                    total_games < 2):
                continue

            pred_by = {'games': [], 'next': 0}
            training_player_data = {'position': player_data['position']}

            for gw_num in range(0, len(gws) - CALIBRATE_BY + 1):
                training_player_data[f"GW{gw_num + 1}"] = gws[gw_num]

            actual_points = 0
            for gw in gws[gw_num:]:
                pred_by['games'].append(gw['diff'])
                actual_points += gw['points']

            if actual_points < CALIBRATE_BY * MIN_SEASON_PPG:
                continue

            if points_sum <= 0 or len(gws) <= CALIBRATE_BY:
                arima = 0
                lstm = 0
            else:
                try:
                    arima = do_arima(list(map(lambda x: x['points'], gws[:-CALIBRATE_BY])), pred_by)[0]
                    lstm = do_lstm(training_player_data, pred_by)[0]
                except:
                    arima = 0
                    lstm = 0

                if arima != 0 and lstm != 0 and (arima / lstm > MAX_DIFF or lstm / arima > MAX_DIFF):
                    arima = 0
                    lstm = 0

            players[team][index] = {'name': player_data['name'], 'arima': arima, 'lstm': lstm,
                                    'actual_points': actual_points}

        players[team] = [player for player in players[team] if
                         'arima' in player and 'lstm' in player and 'name' in player and 'actual_points' in player]

    create_calibration_file()


def create_calibration_file():
    workbook = Workbook(f"./Calibrations/{CURRENT_SEASON}/Week {CURRENT_GAME_WEEK}.xlsx")

    for team in TEAMS:
        players[team] = [player for player in players[team] if player['arima'] != 0 and player['lstm'] != 0]

        if len(players[team]) == 0:
            print(f"Could not find any players for {team}")
            continue

        sheet = workbook.add_worksheet(team)

        arima, lstm = make_calibration(players[team])

        sheet.write_row('H2', ["ARIMA", arima])
        sheet.write_row('H3', ["LSTM", lstm])
        sheet.write_row('H5', ["OFF", f"=SUM(ABS(Table{team}[PP]-Table{team}[AP]))"])
        sheet.write_row('H7', ["AVG", f"=AVERAGE(Table{team}[DIFF])/{CALIBRATE_BY}"])

        columns = list(map(lambda x: {'header': x}, HEADERS))
        columns[HEADERS.index('PP')] = {
            'header': 'PP',
            'formula': "=[@ARIMAPP]*$I$2+[@LSTMPP]*$I$3"
        }
        columns[HEADERS.index('DIFF')] = {
            'header': 'DIFF',
            'formula': "=ABS([@PP]-[@AP])"
        }

        data = list(
            map(lambda player: [player['name'], player['arima'], player['lstm'], "=[@ARIMAPP]*$I$2+[@LSTMPP]*$I$3",
                                player['actual_points'], "=ABS([@PP]-[@AP])"], players[team]))

        sheet.add_table(f"A1:{ALPHABET[len(HEADERS) - 1]}{len(data) + 1}", {'data': data, 'columns': columns,
                                                                            'name': f"Table{team}"})

        sheet.conditional_format('I7', {"type": "3_color_scale", "min_color": "#00FF00", "mid_color": "#FFFF00",
                                        "max_color": "#FF0000", "min_value": 0, "mid_value": 1, "max_value": 2,
                                        "min_type": "num", "mid_type": "num", "max_type": "num"})

    workbook.close()


if __name__ == "__main__":
    init()
