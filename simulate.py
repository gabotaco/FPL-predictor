import os
import json

from dataset import get_dataset
from solver import make_team
from game_information import (get_team_names, PREDICT_BY_WEEKS, TRANSFER_COST, GKPs, DEFs, MIDs, FWDs, TOTAL_PLAYERS,
                              MAX_PER_TEAM)

PREDICTION_DATA_START_YEAR = "2023-24"
PREDICTION_DATA_PREVIOUS_YEAR = "2022-23"

game = {
    "bank": 100,
    "free_transfers": 15,
    "team": [],
    "team_worth": {},
    "score": 0,
    "paid_for_transfers": 0,
}


def init(predict_by_weeks, transfer_cost, gkps, defs, mids, fwds, total_players, max_per_team):
    points_data_set, _ = get_dataset(PREDICTION_DATA_START_YEAR, PREDICTION_DATA_PREVIOUS_YEAR)
    team_names = get_team_names(PREDICTION_DATA_START_YEAR)
    gw_predictions = read_prediction_data(PREDICTION_DATA_START_YEAR, team_names)

    points_map = points_data_set_to_map(points_data_set)

    # Filter out unknown players.
    for prediction in gw_predictions:
        for _ in prediction['players']:
            prediction['players'] = [player for player in prediction['players']
                                     if f"{player['first_name']} {player['last_name']}" in points_map]

    current_gw = 1
    for prediction in gw_predictions:
        print(f"===================== GW {current_gw} =========================== ")

        def set_prev(player):
            player['prev'] = 1 if f"{player['first_name']} {player['last_name']}" in game['team'] else 0
            return player

        team_worth = game['bank'] + calc_team_worth(prediction['players'])
        print(f"Team is worth: ${team_worth}")
        dream_team = make_team(list(map(set_prev, prediction['players'])), predict_by_weeks, transfer_cost,
                               game['free_transfers'], team_worth, team_names, gkps, defs, mids, fwds, total_players,
                               max_per_team)
        num_paid_transfers = update_game(dream_team)
        game['paid_for_transfers'] += num_paid_transfers
        score = score_team(prediction['round'], prediction['players'], num_paid_transfers, points_map)
        game['score'] += score
        print(f"Scored {score} points!")
        current_gw += 1

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


def read_prediction_data(year, teams):
    game_round = 1
    match year:
        case "2017-18":
            game_round = 39
        case "2018-19":
            game_round = 77
        case "2019-20":
            game_round = 115
        case "2020-21":
            game_round = 162
        case "2021-22":
            game_round = 200
        case "2022-23":
            game_round = 238
        case "2023-24":
            game_round = 276
        case "2024-25":
            game_round = 314

    # Filter file's to exclude Challenge files. Then sent from low to high GW.
    predicted_data_files = os.listdir(f"./predictedData/{year}")
    predicted_data_files = [predicted_file_name for predicted_file_name in predicted_data_files
                            if "Challenge" not in predicted_file_name]
    predicted_data_files.sort(key=lambda a: int(a.replace("predictedData", "").replace(".json", "")))

    # Read all predictions for this GW.
    gw_predictions = []
    for predicted_file_name in predicted_data_files:
        current_gw_prediction = {"round": game_round, "players": []}
        with open(f"./predictedData/{year}/{predicted_file_name}", 'r') as predicted_file:
            prediction_file = json.load(predicted_file)
            # Gather indexes.
            first_name_index = prediction_file[0].index("First Name")
            last_name_index = prediction_file[0].index("Surname")
            web_name_index = prediction_file[0].index('Web Name')
            position_index = prediction_file[0].index('Position')
            team_index = prediction_file[0].index('Team')
            cost_index = prediction_file[0].index('Cost')
            pp_index = prediction_file[0].index('PPG') if 'PPG' in prediction_file[0] else prediction_file[0].index(
                'PP')
            next_index = prediction_file[0].index('NEXT')
            for prediction in prediction_file:
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
                for team in teams:
                    player_data[team] = 1 if player_data['team'] == team else 0

                current_gw_prediction['players'].append(player_data)
        gw_predictions.append(current_gw_prediction)
        game_round += 1

    return gw_predictions


if __name__ == "__main__":
    init(PREDICT_BY_WEEKS, TRANSFER_COST, GKPs, DEFs, MIDs, FWDs, TOTAL_PLAYERS, MAX_PER_TEAM)
