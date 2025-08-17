import os
import json
from datetime import datetime, timedelta
from pytz import timezone

from dataset import get_dataset
from solver import make_team
from game_information import (get_team_names, TRANSFER_COST, GKPs, DEFs, MIDs, FWDs, TOTAL_PLAYERS, MAX_PER_TEAM,
                              get_game_round, SEASON_LENGTH, get_team_info, PROCESS_ALL_PLAYERS, BUGGED_PLAYERS)
from main import make_predictions, get_predict_by, MIN_CALIBRATE_BY

DATA_YEAR = "2024-25"
DATA_WEEK_RANGE = (2, 10)
MAKE_PREDICTIONS = True
PREDICTION_TAG = "first10/average/minGames10"

MAX_DIFF = 10
MIN_GAMES = 10
MIN_SEASON_PPG = 1
MIN_SEASON_GAME_PERCENTAGE = 0.8
USE_AVERAGE = True


def get_calibrate_by(gw):
    return SEASON_LENGTH


def get_predict_by_weeks(gw):
    return SEASON_LENGTH + 1 - gw


game = {
    'bank': 0,
    'free_transfers': 1,
    'team': [
        'Kai Havertz',
        'David Raya Martin',
        'Benjamin White',
        'Ollie Watkins',
        'Cole Palmer',
        'Abdoulaye Doucouré',
        'Jordan Pickford',
        'Joachim Andersen',
        'Timothy Castagne',
        'Phil Foden',
        'Julián Álvarez',
        'Kyle Walker',
        'Anthony Gordon',
        'Pedro Porro',
        'Jarrod Bowen'
    ],
    'team_worth': {
        'Gabriel dos Santos Magalhães': 6.1,
        'Kai Havertz': 7.7,
        'Gabriel Martinelli Silva': 6.5,
        'Martin Ødegaard': 8.2,
        'David Raya Martin': 5.6,
        'Declan Rice': 6.3,
        'Bukayo Saka': 10.4,
        'William Saliba': 6.4,
        'Leandro Trossard': 6.7,
        'Benjamin White': 6.2,
        'Norberto Murara Neto': 4.1,
        'Raheem Sterling': 6.7,
        'Leon Bailey': 6.2,
        'Lucas Digne': 4.4,
        'Ezri Konsa Ngoyo': 4.5,
        'Emiliano Martínez Romero': 5.0,
        'John McGinn': 5.2,
        'Youri Tielemans': 5.5,
        'Ollie Watkins': 9.2,
        'Amadou Onana': 4.8,
        'Marcus Rashford': 6.6,
        'Ryan Christie': 4.8,
        'Lewis Cook': 5.0,
        'Antoine Semenyo': 5.7,
        'Marcos Senesi': 4.6,
        'Nathan Collins': 4.6,
        'Vitaly Janelt': 4.8,
        'Mathias Jensen': 5.3,
        'Mads Roerslev Rasmussen': 4.3,
        'Yoane Wissa': 6.9,
        'Lewis Dunk': 4.2,
        'Pascal Groß': 6.5,
        'João Pedro Junqueira de Jesus': 5.5,
        'Moisés Caicedo Corozo': 4.9,
        'Conor Gallagher': 5.9,
        'Cole Palmer': 10.5,
        'Jean-Philippe Mateta': 7.5,
        'Tyrick Mitchell': 4.8,
        'Abdoulaye Doucouré': 5.1,
        'Jarrad Branthwaite': 4.9,
        'Dominic Calvert-Lewin': 5.4,
        'James Garner': 4.9,
        'Dwight McNeil': 5.1,
        'Jordan Pickford': 5.2,
        'James Tarkowski': 4.7,
        'Joachim Andersen': 4.2,
        'Andreas Hoelgebaum Pereira': 4.9,
        'Tom Cairney': 4.8,
        'Timothy Castagne': 4.2,
        'Alex Iwobi': 5.4,
        'Bernd Leno': 5.0,
        'Antonee Robinson': 4.7,
        'Harry Wilson': 5.2,
        'Sander Berge': 5.0,
        'Willian Borges da Silva': 5.0,
        "Dara O'Shea": 3.8,
        'Jordan Ayew': 5.1,
        'Odsonne Edouard': 5.1,
        'Bobby De Cordova-Reid': 5.2,
        'Darwin Núñez Ribeiro': 7.0,
        'Harvey Elliott': 5.2,
        'Cody Gakpo': 7.2,
        'Luis Díaz': 7.5,
        'Mohamed Salah': 13.6,
        'Alexis Mac Allister': 6.2,
        'Virgil van Dijk': 6.7,
        'Bernardo Veiga de Carvalho e Silva': 6.1,
        'Ederson Santana de Moraes': 5.3,
        'Phil Foden': 9.1,
        'Julián Álvarez': 7.0,
        'Kyle Walker': 5.1,
        'Bruno Borges Fernandes': 8.4,
        'Diogo Dalot Teixeira': 5.0,
        'Alejandro Garnacho': 5.9,
        'Scott McTominay': 4.9,
        'Miguel Almirón Rejala': 5.4,
        'Bruno Guimarães Rodriguez Moura': 6.2,
        'Dan Burn': 4.6,
        'Anthony Gordon': 7.4,
        'Sean Longstaff': 4.4,
        'Fabian Schär': 5.5,
        'Anthony Elanga': 5.5,
        'Morgan Gibbs-White': 6.5,
        'Chris Wood': 7.2,
        'Ryan Yates': 4.8,
        'Pierre-Emile Højbjerg': 5.0,
        'Brennan Johnson': 6.2,
        'Dejan Kulusevski': 6.2,
        'Pedro Porro': 5.2,
        'Cristian Romero': 4.9,
        'Pape Matar Sarr': 4.7,
        'Son Heung-min': 9.7,
        'Alphonse Areola': 4.2, 'Jarrod Bowen': 7.9, 'Emerson Palmieri dos Santos': 4.4, 'Max Kilman': 4.3,
        'Lucas Tolentino Coelho de Lima': 5.7, 'James Ward-Prowse': 6.1, 'Kurt Zouma': 4.4, 'Rayan Aït-Nouri': 5.1,
        'Matheus Santos Carneiro Da Cunha': 7.0, 'João Victor Gomes da Silva': 4.9, 'José Malheiro de Sá': 4.4,
        'Mario Lemina': 4.8, 'Nélson Cabral Semedo': 4.5, 'Toti António Gomes': 4.3},
    'score': 48,
    'paid_for_transfers': 0}


def init(transfer_cost, gkps, defs, mids, fwds, total_players, max_per_team, season_length, min_games,
         process_all_players, min_season_ppg, min_season_game_percentage, bugged_players, use_average, max_diff):
    first_game_round = get_game_round(DATA_YEAR)
    min_gw, max_gw = DATA_WEEK_RANGE
    points_data_set, master_data_set = get_dataset(DATA_YEAR, max_gw, True)
    team_names = get_team_names(DATA_YEAR)
    team_info = get_team_info(DATA_YEAR)
    points_map = points_data_set_to_map(points_data_set)

    os.makedirs(f"./simulationData/{DATA_YEAR}/{PREDICTION_TAG}", exist_ok=True)

    for gw in range(min_gw, max_gw + 1):
        predict_by_weeks = get_predict_by_weeks(gw)
        calibrate_by = get_calibrate_by(gw)
        prediction = simulate_prediction(DATA_YEAR, gw, predict_by_weeks, team_info, team_names, points_data_set,
                                         master_data_set, calibrate_by, season_length, min_games, process_all_players,
                                         min_season_ppg, min_season_game_percentage, bugged_players, use_average,
                                         max_diff) if MAKE_PREDICTIONS else read_prediction_data(DATA_YEAR, gw,
                                                                                                 team_names)

        # Filter out unknown players.
        prediction = [player for player in prediction
                      if f"{player['first_name']} {player['last_name']}" in points_map]

        print(f"===================== GW {gw} =========================== ")

        def set_prev(player):
            player['prev'] = 1 if f"{player['first_name']} {player['last_name']}" in game['team'] else 0
            return player

        team_worth = game['bank'] + calc_team_worth(prediction)
        print(f"Team is worth: ${team_worth}")
        dream_team = make_team(list(map(set_prev, prediction)), predict_by_weeks, transfer_cost, game['free_transfers'],
                               team_worth, team_names, gkps, defs, mids, fwds, total_players, max_per_team)
        num_paid_transfers = update_game(dream_team)
        game['paid_for_transfers'] += num_paid_transfers
        score = score_team(first_game_round + gw - 1, prediction, num_paid_transfers, points_map)
        game['score'] += score
        print(f"Scored {score} points!")

    print("===================== THE END =========================== ")
    print(f"At the end of the season you scored {game['score']} points!")
    print(f"You paid for {game['paid_for_transfers']} transfers.")


def score_team(gw_round, players, paid_for_transfers, points_map):
    player_points = []
    for player in players:
        if f"{player['first_name']} {player['last_name']}" in game['team']:
            player_points.append(player)

    # Pick subs.
    player_points.sort(key=lambda a: a['next'], reverse=True)
    # Filter out players who didn't play.
    player_points = [player for player in player_points
                     if f"GW{gw_round}" in points_map[f"{player['first_name']} {player['last_name']}"]]
    # Get actual points.
    for player in player_points:
        player['actual'] = points_map[f"{player['first_name']} {player['last_name']}"][f"GW{gw_round}"]['points']

    team_points = 0
    num_gkp = 0
    num_def = 0
    num_mid = 0
    num_fwd = 0

    def enough_space_for_defenders():
        # Always need at least 3 defenders
        if num_def >= 3:
            return True

        # Always assume we have 1 goalie. Add 1 for the current player.
        num_players_selected = 1 + 3 + num_mid + num_fwd + 1
        return num_players_selected <= 11

    def enough_space_for_forwards():
        # Always need at least 1 forward.
        if num_fwd >= 1:
            return True

        num_players_selected = 1 + num_def + num_mid + 1 + 1
        return num_players_selected <= 11

    for player in player_points:
        if player['position'] == 'GKP':
            # Only 1 GKP allowed.
            if num_gkp == 1:
                continue
            num_gkp += 1
        elif player['position'] == 'DEF':
            if enough_space_for_forwards():
                num_def += 1
            else:
                continue
        elif player['position'] == 'MID':
            if enough_space_for_defenders() and enough_space_for_forwards():
                num_mid += 1
            else:
                continue
        elif player['position'] == 'FWD':
            if enough_space_for_defenders():
                num_fwd += 1
            else:
                continue

        # Captain
        if player['name'] == player_points[0]['name']:
            team_points += player['actual'] * 2
        else:
            team_points += player['actual']

        if num_gkp + num_def + num_mid + num_fwd == 11:
            break

    if num_gkp + num_def + num_mid + num_fwd != 11:
        print(f"ONLY FIELDED {num_gkp + num_def + num_mid + num_fwd} PLAYERS!!!!!!!!!!!")

    return team_points - paid_for_transfers * 4


def calc_team_worth(players):
    # Update known costs.
    for player in players:
        game['team_worth'][f"{player['first_name']} {player['last_name']}"] = player['cost']

    team_worth = 0
    for player_name in game['team']:
        team_worth += game['team_worth'][player_name]

    return team_worth


def update_game(new_team):
    num_transfers = 0
    money_spent = 0
    money_gained = 0

    for player in game['team']:
        if player not in new_team:
            # Transferred out.
            money_gained += game['team_worth'][player]
            print(f"Transferred out {player}")
    for player in new_team:
        if player not in game['team']:
            # Just bought.
            num_transfers += 1
            money_spent += game['team_worth'][player]
            print(f"Bought {player}")

    game['team'] = new_team

    if game['free_transfers'] == 15:
        game['bank'] = 100 - money_spent
    else:
        game['bank'] = game['bank'] - money_spent + money_gained

    num_paid_transfers = max(num_transfers - game['free_transfers'], 0)

    game['free_transfers'] -= num_transfers

    if game['free_transfers'] < 1:
        game['free_transfers'] = 1
    elif game['free_transfers'] < 5:
        game['free_transfers'] += 1

    print(f"Made {num_transfers} transfers.")

    return num_paid_transfers


def points_data_set_to_map(points_data_set):
    points_map = {}
    for _, player_data in points_data_set.items():
        points_map[f"{player_data['first_name']} {player_data['last_name']}"] = player_data

    return points_map


def simulate_prediction(year, gw, predict_by_weeks, team_info, team_names, points_data_set,
                        unfinished_master_data_set, calibrate_by, season_length, min_games, process_all_players,
                        min_season_ppg, min_season_game_percentage, bugged_players, use_average, max_diff):
    eta = datetime.now(timezone('US/Eastern')) + timedelta(minutes=8, seconds=30)
    print(f"Getting prediction for GW{gw}. ETA {eta.strftime("%I:%M%p")}")
    predict_by = get_predict_by(year, gw, predict_by_weeks, team_info, team_names)
    filename = f"./simulationData/{year}/{PREDICTION_TAG}/{gw}.json"
    master_data_set, _ = make_predictions(year, gw, True, points_data_set, unfinished_master_data_set,
                                          calibrate_by, season_length, min_games, process_all_players,
                                          min_season_ppg, predict_by, predict_by_weeks, filename,
                                          min_season_game_percentage, bugged_players.copy(), use_average, max_diff,
                                          game['team'], [])

    return process_master_data(master_data_set, team_names)


def read_prediction_data(year, gw, team_names):
    if not os.path.isfile(f"./predictedData/{year}/predictedData{gw}.json"):
        raise f"Could not find GW{gw} in the prediction data."

    with open(f"./predictedData/{year}/predictedData{gw}.json", 'r') as predicted_file:
        prediction_file = json.load(predicted_file)
        return process_master_data(prediction_file, team_names)


def process_master_data(master_data_set, team_names):
    players = []
    # Gather indexes.
    first_name_index = master_data_set[0].index("First Name")
    last_name_index = master_data_set[0].index("Surname")
    web_name_index = master_data_set[0].index('Web Name')
    position_index = master_data_set[0].index('Position')
    team_index = master_data_set[0].index('Team')
    cost_index = master_data_set[0].index('Cost')
    pp_index = master_data_set[0].index('PPG') if 'PPG' in master_data_set[0] else master_data_set[0].index(
        'PP')
    next_index = master_data_set[0].index('NEXT')
    for prediction in master_data_set:
        # Skip header
        if prediction[0] == 'First Name':
            continue
        # Skip player who doesn't have a prediction.
        if len(prediction) <= next_index:
            continue

        player_data = {
            "first_name": prediction[first_name_index],
            "last_name": prediction[last_name_index],
            "name": prediction[web_name_index],
            "pp": prediction[pp_index],
            "next": prediction[next_index],
            "position": prediction[position_index],
            "team": prediction[team_index],
            "cost": prediction[cost_index],
            "gkp": 1 if prediction[position_index] == "GKP" else 0,
            "def": 1 if prediction[position_index] == "DEF" else 0,
            "mid": 1 if prediction[position_index] == "MID" else 0,
            "fwd": 1 if prediction[position_index] == "FWD" else 0,
            "health": 1,
        }
        for team in team_names:
            player_data[team] = 1 if player_data['team'] == team else 0

        players.append(player_data)

    return players


if __name__ == "__main__":
    init(TRANSFER_COST, GKPs, DEFs, MIDs, FWDs, TOTAL_PLAYERS, MAX_PER_TEAM, SEASON_LENGTH, MIN_GAMES,
         PROCESS_ALL_PLAYERS, MIN_SEASON_PPG, MIN_SEASON_GAME_PERCENTAGE, BUGGED_PLAYERS, USE_AVERAGE, MAX_DIFF)
