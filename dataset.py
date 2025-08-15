import csv
import os

from game_information import get_team_info, POSITIONS, get_game_round, get_team_names, get_next_year, get_previous_year

USE_UNDERSTAT = False
NO_NEW_PLAYERS = False

STARTING_SEASON = "2019-20" if USE_UNDERSTAT else "2018-19"

OLD_PLAYERS = []
UNDERSTAT_NAME_MAP = {}


def get_previous_players(current_season):
    previous_players = set()

    with open(f"./Fantasy-Premier-League/data/{get_previous_year(current_season)}/players_raw.csv", 'r') as data_file:
        csv_reader = csv.DictReader(data_file)

        for row in csv_reader:
            player_name = f"{row['first_name']} {row['second_name']}"
            if player_name in previous_players:
                raise Exception("2 players have the same name")
            previous_players.add(player_name)

    return previous_players


def get_pids_and_master_data_set(previous_players, team_info, team_names, current_season, header):
    pids = {}
    master_data_set = [header]

    with open(f"./Fantasy-Premier-League/data/{current_season}/players_raw.csv") as data_file:
        csv_reader = csv.DictReader(data_file)

        for i, row in enumerate(csv_reader):
            player_position = POSITIONS[int(row['element_type'])]
            if player_position == 'MNG':
                continue

            player = [row['first_name'], row['second_name'], row['web_name'], player_position,
                      1 if player_position == 'GKP' else 0, 1 if player_position == 'DEF' else 0,
                      1 if player_position == 'MID' else 0, 1 if player_position == 'FWD' else 0,
                      team_info[int(row['team'])]['short_name']]

            for team_name in team_names:
                if team_info[int(row['team'])]['short_name'] == team_name:
                    player.append(1)
                else:
                    player.append(0)

            player.append(int(row['now_cost']) / 10)
            player.append(i)

            player_name = f"{row['first_name']} {row['second_name']}"
            if player_name in pids:
                raise Exception("2 players with the same name! " + player_name)

            if previous_players is None or player_name in previous_players:
                pids[player_name] = {'id': i, 'web_name': row['web_name'], 'first_name': row['first_name'],
                                     'last_name': row['second_name'], 'team': team_info[int(row['team'])]['short_name'],
                                     'position': player_position}
                master_data_set.append(player)

    return pids, master_data_set


def load_understat(current_season, pids):
    understat_players = os.listdir(f"./Fantasy-Premier-League/data/{current_season}/understat")
    understat_players = [player for player in understat_players if not player.startswith("understat")]

    for i, understat_player in enumerate(understat_players):
        name = ' '.join(understat_player.split("_")[:-1]).replace('&#039;', '\'')

        if name in OLD_PLAYERS:
            continue

        if name in UNDERSTAT_NAME_MAP:
            name = UNDERSTAT_NAME_MAP[name]

        if name not in pids:
            raise Exception(f"Didn't find a player with the name {name}")

        pids[name]['understat'] = {}

        with open(f"./Fantasy-Premier-League/data/{current_season}/understat/{understat_player}") as understat_file:
            understat_reader = csv.DictReader(understat_file)

            for player_element in understat_reader:
                pids[name]['understat'][player_element['date']] = player_element


def get_elements_to_use(year, pids):
    elements_to_use = {}

    with open(f"./Fantasy-Premier-League/data/{year}/player_idlist.csv") as player_file:
        csv_reader = csv.DictReader(player_file)

        for player_id in csv_reader:
            player_name = f"{player_id['first_name']} {player_id['second_name']}"
            if player_name in pids:
                elements_to_use[player_name] = pids[player_name]

    return elements_to_use


def get_fixture_maps(year, team_info):
    fixture_to_difficulty = {}
    fixture_to_team = {}

    with open(f"./Fantasy-Premier-League/data/{year}/fixtures.csv") as fixture_file:
        fixture_reader = csv.DictReader(fixture_file)

        for fixture in fixture_reader:
            fixture_to_difficulty[int(fixture['id'])] = {'h': int(fixture['team_h_difficulty']),
                                                         'a': int(fixture['team_a_difficulty'])}
            fixture_to_team[int(fixture['id'])] = {'h': team_info[int(fixture['team_h'])]['short_name'],
                                                   'a': team_info[int(fixture['team_a'])]['short_name']}

    return fixture_to_difficulty, fixture_to_team


def get_points(year, team_info, pids, current_game_week, current_season, is_simulation, points_data_set=None):
    if points_data_set is None:
        points_data_set = {}

    elements_to_use = get_elements_to_use(year, pids)
    fixture_to_difficulty, fixture_to_team = get_fixture_maps(year, team_info)
    game_round = get_game_round(year)

    gws = os.listdir(f"./Fantasy-Premier-League/data/{year}/gws") if is_simulation or year != current_season or current_game_week > 1 \
        else []
    gws = [gw for gw in gws if gw.startswith("gw")]
    gws.sort(key=lambda a: int(a.replace("gw", "").replace(".csv", "")))

    found_previous_game_week = False

    for gw in gws:
        gw_number = int(gw.replace("gw", "").replace(".csv", ""))
        if gw_number == current_game_week - 1:
            found_previous_game_week = True

        with open(f"./Fantasy-Premier-League/data/{year}/gws/{gw}", encoding="latin-1") as gw_file:
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

                if USE_UNDERSTAT and 'understat' not in element_object:
                    print(f"No understats found for {name}")
                    continue

                if element_object['id'] not in points_data_set:
                    points_data_set[element_object['id']] = {'first_name': element_object['first_name'],
                                                             'last_name': element_object['last_name'],
                                                             'name': element_object['web_name'],
                                                             'team': element_object['team'], 'id': element_object['id'],
                                                             'position': element_object['position']}

                diff = fixture_to_difficulty[int(gw_element['fixture'])][
                    'h' if gw_element['was_home'] == 'True' else 'a']
                opp_team = fixture_to_team[int(gw_element['fixture'])]['a' if gw_element['was_home'] == 'True' else 'h']

                fixture_date = gw_element['kickoff_time'].split('T')[0]
                if USE_UNDERSTAT and fixture_date not in element_object['understat']:
                    print(f"No understats found for {name} for {fixture_date}")
                    continue

                points_data_set[element_object['id']][f"GW{game_round}"] = {'diff': diff,
                                                                            'points': int(gw_element['total_points']),
                                                                            'team': opp_team}
        game_round += 1

    if current_season == year and current_game_week > 1 and not found_previous_game_week:
        raise "Didn't find data for the previous GW. Did you pull the new data?"

    next_year = get_next_year(year, current_season)
    if next_year is not None:
        return get_points(next_year, team_info, pids, current_game_week, current_season, is_simulation, points_data_set)

    return points_data_set


def get_header(team_names):
    return ["First Name", "Surname", "Web Name", "Position", "GKP", "DEF", "MID", "FWD", "Team",
            *team_names, "Cost", "ID", "ARIMA", "LSTM", "PP", "NEXT", "Health", "PREV",
            "Selected"]


def get_dataset(current_season, current_game_week, is_simulation=False):
    team_names = get_team_names(current_season)
    team_info = get_team_info(current_season)

    previous_players = get_previous_players(current_season) if NO_NEW_PLAYERS else None
    pids, master_data_set = get_pids_and_master_data_set(previous_players, team_info, team_names, current_season,
                                                         get_header(team_names))
    if USE_UNDERSTAT:
        load_understat(current_season, pids)

    points_data_set = get_points(STARTING_SEASON, team_info, pids, current_game_week, current_season, is_simulation)

    return points_data_set, master_data_set
