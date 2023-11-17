import csv
import json
import os

from game_information import TEAMS, get_team_info, PREVIOUS_SEASON, CURRENT_SEASON, POSITIONS, CURRENT_GAME_WEEK

STARTING_SEASON = "2018-19"

NO_NEW_PLAYERS = False

PIDs = {}
teams = {}
points_data_set = {}
master_data_set = [
    ["First Name", "Surname", "Web Name", "Position", "GKP", "DEF", "MID", "FWD", "Team", *TEAMS, "Cost", "ID", "ARIMA",
     "LSTM", "PPG", "NEXT", "PREV", "Selected"]]


def get_teams():
    global teams
    teams = get_team_info()

    if NO_NEW_PLAYERS:
        get_previous_players_then_current_players()
    else:
        get_current_players(None)


def get_previous_players_then_current_players():
    with open(f"../Fantasy-Premier-League/data/{PREVIOUS_SEASON}/players_raw.csv", 'r') as data_file:
        csv_reader = csv.DictReader(data_file)

        previous_players = set()
        for row in csv_reader:
            player_name = f"{row['first_name']} {row['second_name']}"
            if player_name in previous_players:
                raise Exception("2 players have the same name")
            previous_players.add(player_name)

    get_current_players(previous_players)


def get_current_players(previous_players):
    global master_data_set, PIDs, teams
    with open(f"../Fantasy-Premier-League/data/{CURRENT_SEASON}/players_raw.csv") as data_file:
        csv_reader = csv.DictReader(data_file)

        for i, row in enumerate(csv_reader):
            player_position = POSITIONS[int(row['element_type'])]
            player = [row['first_name'], row['second_name'], row['web_name'], player_position,
                      1 if player_position == 'GKP' else 0, 1 if player_position == 'DEF' else 0,
                      1 if player_position == 'MID' else 0, 1 if player_position == 'FWD' else 0,
                      teams[int(row['team'])]['short_name']]

            for team_name in TEAMS:
                if teams[int(row['team'])]['short_name'] == team_name:
                    player.append(1)
                else:
                    player.append(0)

            player.append(int(row['now_cost']) / 10)
            player.append(i)

            player_name = f"{row['first_name']} {row['second_name']}"
            if player_name in PIDs:
                raise Exception("2 players with the same name!")

            if previous_players is None or player_name in previous_players:
                PIDs[player_name] = {'id': i, 'web_name': row['web_name'], 'first_name': row['first_name'],
                                     'last_name': row['second_name'], 'team': teams[int(row['team'])]['short_name'],
                                     'position': player_position}
                master_data_set.append(player)

    get_points(STARTING_SEASON)


def get_points(year):
    global PIDs, points_data_set
    with open(f"../Fantasy-Premier-League/data/{year}/player_idlist.csv") as player_file:
        csv_reader = csv.DictReader(player_file)

        elements_to_use = {}
        used_players = set()

        for playerId in csv_reader:
            player_name = f"{playerId['first_name']} {playerId['second_name']}"
            if player_name in PIDs:
                elements_to_use[player_name] = PIDs[player_name]
                used_players.add(PIDs[player_name]['id'])

    with open(f"../Fantasy-Premier-League/data/{year}/fixtures.csv") as fixture_file:
        fixture_reader = csv.DictReader(fixture_file)

        fixture_to_difficulty = {}

        for fixture in fixture_reader:
            fixture_to_difficulty[int(fixture['id'])] = {'h': int(fixture['team_h_difficulty']),
                                                         'a': int(fixture['team_a_difficulty'])}

    gws = os.listdir(f"../Fantasy-Premier-League/data/{year}/gws")
    gws = [gw for gw in gws if gw.startswith("gw")]

    gws.sort(key=lambda a: int(a.replace("gw", "").replace(".csv", "")))

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

    for gw in gws:
        with open(f"../Fantasy-Premier-League/data/{year}/gws/{gw}", encoding="latin-1") as gw_file:
            gw_reader = csv.DictReader(gw_file)

            for gw_element in gw_reader:
                if '_' in gw_element['name']:
                    name = ' '.join(gw_element['name'].split("_")[:-1])
                else:
                    name = gw_element['name']

                try:
                    name = name.encode("latin-1").decode("utf8")
                except:
                    name = name

                if name not in elements_to_use or int(gw_element['minutes']) == 0:
                    continue

                element_object = elements_to_use[name]

                if element_object['id'] not in points_data_set:
                    points_data_set[element_object['id']] = {'first_name': element_object['first_name'],
                                                             'last_name': element_object['last_name'],
                                                             'name': element_object['web_name'],
                                                             'team': element_object['team'], 'id': element_object['id'],
                                                             'position': element_object['position']}

                diff = fixture_to_difficulty[int(gw_element['fixture'])][
                    'h' if gw_element['was_home'] == 'True' else 'a']

                points_data_set[element_object['id']][f"GW{game_round}"] = {'diff': diff,
                                                                            'points': int(gw_element['total_points'])}

        game_round += 1

    match year:
        case "2016-17":
            get_points("2017-18")
        case "2017-18":
            get_points("2018-19")
        case "2018-19":
            get_points("2019-20")
        case "2019-20":
            get_points("2020-21")
        case "2020-21":
            get_points("2021-22")
        case "2021-22":
            get_points("2022-23")
        case "2022-23":
            get_points("2023-24")
        case "2023-24":
            write_points_data()


def write_points_data():
    global points_data_set
    with open(f"./datasets/{CURRENT_SEASON}/dataset{CURRENT_GAME_WEEK}.json", 'w') as dataset_file:
        json.dump(points_data_set, dataset_file, ensure_ascii=False, indent=4)


def get_dataset():
    global points_data_set, master_data_set
    get_teams()
    return points_data_set, master_data_set
