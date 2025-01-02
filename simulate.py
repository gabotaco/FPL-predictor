import os
import json
from datetime import datetime, timedelta
from pytz import timezone

from dataset import get_dataset
from solver import make_team
from game_information import (get_team_names, TRANSFER_COST, GKPs, DEFs, MIDs, FWDs, TOTAL_PLAYERS, MAX_PER_TEAM,
                              get_game_round, SEASON_LENGTH, get_team_info, PROCESS_ALL_PLAYERS, BUGGED_PLAYERS)
from main import make_predictions, get_predict_by

DATA_YEAR = "2023-24"
DATA_WEEK_RANGE = (19, 38)
MAKE_PREDICTIONS = True
PREDICTION_TAG = "maxCalAndPred/minPpg1"

MAX_DIFF = 10
MIN_GAMES = 3
MIN_SEASON_PPG = 1
MIN_SEASON_GAME_PERCENTAGE = 0.7
USE_AVERAGE = False

game = {
    "bank": 100,
    "free_transfers": 15,
    "team": [],
    "team_worth": {},
    "score": 0,
    "paid_for_transfers": 0,
}


def init(transfer_cost, gkps, defs, mids, fwds, total_players, max_per_team, season_length, min_games,
         process_all_players, min_season_ppg, min_season_game_percentage, bugged_players, use_average, max_diff):
    first_game_round = get_game_round(DATA_YEAR)
    min_gw, max_gw = DATA_WEEK_RANGE
    points_data_set, master_data_set = get_dataset(DATA_YEAR, max_gw)
    team_names = get_team_names(DATA_YEAR)
    team_info = get_team_info(DATA_YEAR)
    points_map = points_data_set_to_map(points_data_set)

    os.makedirs(f"./simulationData/{DATA_YEAR}/{PREDICTION_TAG}", exist_ok=True)

    for gw in range(min_gw, max_gw + 1):
        predict_by_weeks = max_gw + 1 - gw
        calibrate_by = gw - 1
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
    eta = datetime.now(timezone('EST')) + timedelta(minutes=8, seconds=30)
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
