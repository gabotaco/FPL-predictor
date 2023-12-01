import csv

CURRENT_GAME_WEEK = 14

CURRENT_SEASON = "2023-24"
PREVIOUS_SEASON = "2022-23"
TEAMS = ['ARS', 'AVL', 'BOU', 'BRE', 'BHA', 'BUR', 'CHE', 'CRY', 'EVE', 'FUL', 'LIV', 'LUT', 'MCI', 'MUN', 'NEW', 'NFO',
         'SHU', 'TOT', 'WHU', 'WOL']
CURRENT_SEASON_BEGINNING_ROUND = 273

SEASON_LENGTH = 36

MIN_GAMES = 3
MIN_SEASON_PPG = 2
MIN_SEASON_GAME_PERCENTAGE = 0.7
POSITIONS = {1: 'GKP', 2: 'DEF', 3: 'MID', 4: 'FWD'}


def get_team_info():
    with open(f"../Fantasy-Premier-League/data/{CURRENT_SEASON}/teams.csv", 'r') as data_file:
        csv_reader = csv.DictReader(data_file)

        teams = {}
        for team in csv_reader:
            teams[int(team['id'])] = {'short_name': team['short_name'], 'long_name': team['name'],
                                      'pulse': int(team['pulse_id'])}

        return teams