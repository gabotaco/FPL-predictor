import csv

CURRENT_GAME_WEEK = 3
TEAM_WORTH = 99.1 + 1.0
FREE_TRANSFERS = 1
CHALLENGE_TEAM = False
CURRENT_TEAM = {
    "Nick Pope Pope",
    "Matz Sels Sels",

    "Trevoh Chalobah Chalobah",
    "Marc Guéhi Guéhi",
    "Diogo Dalot Teixeira Dalot",
    "Ola Aina Aina",
    "Aaron Wan-Bissaka Wan-Bissaka",

    "Antoine Semenyo Semenyo",
    "Eberechi Eze Eze",
    "Mohamed Salah M.Salah",
    "Bryan Mbeumo Mbeumo",
    "Jacob Murphy J.Murphy",

    "Danny Welbeck Welbeck",
    "Chris Wood Wood",
    "Jarrod Bowen Bowen",
}
INJURIES = {
    "Yoane Wissa Wissa": 0,
    "Nicolas Jackson N.Jackson": 0,
}

BUGGED_PLAYERS = []

TRANSFER_COST = 4
GKPs = (2, 2)
DEFs = (5, 5)
MIDs = (5, 5)
FWDs = (3, 3)
TOTAL_PLAYERS = 15
MAX_PER_TEAM = 3

PROCESS_ALL_PLAYERS = False
USE_AVERAGE = True
CURRENT_SEASON = "2025-26"
SEASON_LENGTH = 38

MIN_GAMES = 3
MIN_SEASON_PPG = 1
MIN_SEASON_GAME_PERCENTAGE = 0.7

POSITIONS = {1: 'GKP', 2: 'DEF', 3: 'MID', 4: 'FWD', 5: 'MNG'}


def get_game_round(year):
    match year:
        case "2016-17":
            return 1
        case "2017-18":
            return 39
        case "2018-19":
            return 77
        case "2019-20":
            return 115
        case "2020-21":
            return 162
        case "2021-22":
            return 200
        case "2022-23":
            return 238
        case "2023-24":
            return 276
        case "2024-25":
            return 314
        case "2025-26":
            return 352

    raise "Invalid game round year"


def get_next_year(year, current_season):
    if year == current_season:
        return None

    match year:
        case "2016-17":
            return "2017-18"
        case "2017-18":
            return "2018-19"
        case "2018-19":
            return "2019-20"
        case "2019-20":
            return "2020-21"
        case "2020-21":
            return "2021-22"
        case "2021-22":
            return "2022-23"
        case "2022-23":
            return "2023-24"
        case "2023-24":
            return "2024-25"
        case "2024-25":
            return "2025-26"

    raise "Invalid next year"


def get_previous_year(year):
    match year:
        case "2017-18":
            return "2016-17"
        case "2018-19":
            return "2017-18"
        case "2019-20":
            return "2018-19"
        case "2020-21":
            return "2019-20"
        case "2021-22":
            return "2020-21"
        case "2022-23":
            return "2021-22"
        case "2023-24":
            return "2022-23"
        case "2024-25":
            return "2023-24"
        case "2025-26":
            return "2024-25"

    raise "Invalid previous year"


def get_team_info(season):
    with open(f"./Fantasy-Premier-League/data/{season}/teams.csv", 'r') as data_file:
        csv_reader = csv.DictReader(data_file)

        teams = {}
        for team in csv_reader:
            teams[int(team['id'])] = {'short_name': team['short_name'], 'long_name': team['name'],
                                      'pulse': int(team['pulse_id'])}

        return teams


def get_team_names(season):
    team_info = get_team_info(season)
    team_names = []

    for team_id in team_info:
        team_names.append(team_info[team_id]['short_name'])

    return team_names
