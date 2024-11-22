import csv
import json
import os

from game_information import TEAMS, get_team_info, PREVIOUS_SEASON, CURRENT_SEASON, POSITIONS, CURRENT_GAME_WEEK, CHALLENGE_TEAM

USE_UNDERSTAT = False
NO_NEW_PLAYERS = False

STARTING_SEASON = "2019-20" if USE_UNDERSTAT else "2018-19"

PIDs = {}
teams = {}
points_data_set = {}
master_data_set = [
    ["First Name", "Surname", "Web Name", "Position", "GKP", "DEF", "MID", "FWD", "Team", *TEAMS, "Cost", "ID", "ARIMA",
     "LSTM", "FOREST", "PP", "NEXT", "Health", "PREV", "Selected"]]

# Check Sasa Kalajdzic and Martin Dubravka and Josh Acheampong
old_players = ["Gonzalo Montiel", "Auston Trusty", "Willian", "Said Benrahma", "Sergio Gómez", "Ivo Grbic",
               "Michael Olise", "Jayden Danns", "Finley Munroe", "Donny van de Beek", "Marc Guehi", "Nuno Tavares",
               "Mason Burstow", "Tom Davies", "Andrey Santos", "Serge Aurier", "James Tomkins", "Bertrand Traoré",
               "Ivan Perisic", "Aaron Ramsey", "Vitinho", "Albert Sambi Lokonga", "Mads Andersen", "John Fleck",
               "Chris Basham", "Divock Origi", "Oliver Arblaster", "Antwoine Hackford", "Maxime Estève", "Bénie Traoré",
               "Cauley Woodrow", "Alfie Doughty", "Reece Burke", "Zeki Amdouni", "Han-Noah Massengo", "Sofyan Amrabat",
               "Kaide Gordon", "Jordan Clark", "Jacob Bruun Larsen", "Mike Trésor", "Dominic Sadi", "Benson Manuel",
               "Yunus Konak", "Marcus Harness", "Chiquinho", "Thomas Cannon", "Aymeric Laporte", "Jacob Brown",
               "André Gomes", "Eric Dier", "Angelo Ogbonna", "Pelly Ruddock Mpanzu", "Facundo Pellistri",
               "Andros Townsend", "Saman Ghoddos", "Thiago Silva", "Josh Brownhill", "Hannes Delcroix",
               "Michael Ndiweni", "Sam Curtis", "Ben Osborn", "Daniel Gore", "Teden Mengi", "Jairo Riedewald",
               "Lyle Foster", "Brandon Aguilera", "Amari'i Bell", "Zack Nelson", "Anel Ahmedhodzic",
               "Pablo Fornals", "Ben Parkinson", "Sydie Peck", "Nicolo Zaniolo", "Luca Koleosho", "Martin Dubravka",
               "Anis Ben Slimane", "Connor Roberts", "Fabio Silva", "Anssumane Fati", "Loris Karius",
               "Aleksandar Mitrovic", "Rhian Brewster", "Hjalmar Ekdal", "Ryan Oné", "Chimuanya Ugochukwu",
               "Marvelous Nakamba", "Oliver Norwood", "Ameen Al Dakhil", "Jack Cork", "Cheikhou Kouyaté",
               "Joe Rothwell", "Max Lowe", "Davinson Sánchez", "Elijah Adebayo", "Sávio", "Rhys Norrington-Davies",
               "Carlton Morris", "Cédric Soares", "Gabriel Osho", "Willy Kambwala", "Michael Olakigbe", "Omari Forson",
               "Scott McKenna", "Ionut Radu", "Josh Cullen", "Stefan Bajcetic", "Calum Chambers", "Thomas Strakosha",
               "Anass Zaroury", "Johann Berg Gudmundsson", "Joseph Johnson", "Vinicius Souza", "Ben Godfrey",
               "Giovanni Reyna", "Sasa Kalajdzic", "Felipe", "Daniel Podence", "Fred Onyedinma", "Jimi Tauriainen",
               "Rodrigo Ribeiro", "John Egan", "Louis Beyer", "Andre Brooks", "George Baldock", "Jay Rodriguez",
               "Arnaut Danjuma Groeneveld", "João Palhinha", "Mohamed Elneny", "Tahith Chong", "Luke Berry",
               "Joel Matip", "Tom Lockyer", "Ryan John Giles", "Lewis Warrington", "Kieffer Moore", "Raphael Varane",
               "Philippe Coutinho", "Owen Beck", "Douglas Luiz", "Nathan Redmond", "Lorenz Assignon", "Moussa Niakhate",
               "Daiki Hashioka", "Divin Mubama", "Amadou Diallo", "Clement Lenglet", "Carlos Alcaraz",
               "Oliver McBurnie", "Anthony Martial", "Thiago Alcántara", "James Shea", "Shandon Baptiste", "Fode Toure",
               "Álex Moreno", "Jamie Donley", "Thomas Kaminski", "Michael Obafemi", "Gustavo Hamer", "Yasser Larouci",
               "Matt Ritchie", "Jayden Bogle", "Alex Matos", "James Trafford", "Rodri", "Thilo Kehrer", "Tyler Onyango",
               "Jack Robinson", "Josh Acheampong", "Paul Dummett"]
understat_name_map = {"Amad Diallo Traore": "Amad Diallo", "Takehiro Tomiyasu": "Tomiyasu Takehiro",
                      "Andreas Pereira": "Andreas Hoelgebaum Pereira", "Sammie Szmodics": "Sam Szmodics",
                      "Lukasz Fabianski": "Łukasz Fabiański", "Jota Silva": "João Pedro Ferreira Silva",
                      "Antony": "Antony Matheus dos Santos", "Yukinari Sugawara": "Sugawara Yukinari",
                      "Ben White": "Benjamin White", "Benoit Badiashile Mukinayi": "Benoît Badiashile",
                      "Bernardo Silva": "Bernardo Veiga de Carvalho e Silva", "Nikola Milenkovic": "Nikola Milenković",
                      "Beto": "Norberto Bercique Gomes Betuncal", "Bobby Reid": "Bobby De Cordova-Reid",
                      "Boubacar Traore": "Boubacar Traoré", "Bruno Fernandes": "Bruno Borges Fernandes",
                      "Bruno Guimarães": "Bruno Guimarães Rodriguez Moura", "Casemiro": "Carlos Henrique Casimiro",
                      "Carlos Forbs": "Carlos Roberto Forbs Borges", "João Félix": "João Félix Sequeira",
                      "Cheick Oumar Doucoure": "Cheick Doucouré", "Kosta Nedeljkovic": "Kosta Nedeljković",
                      "Dominic Solanke": "Dominic Solanke-Mitchell", "Radu Dragusin": "Radu Drăgușin",
                      "Danilo": "Danilo dos Santos de Oliveira", "Fabio Carvalho": "Fábio Freitas Gouveia Carvalho",
                      "Darwin Núñez": "Darwin Núñez Ribeiro", "David Raya": "David Raya Martin",
                      "Deivid Washington": "Deivid Washington de Souza Eugênio", "Marc Guiu": "Marc Guiu Paz",
                      "Diego Carlos": "Diego Carlos Santos Silva", "Diogo Dalot": "Diogo Dalot Teixeira",
                      "Diogo Jota": "Diogo Teixeira da Silva", "Djordje Petrovic": "Đorđe Petrović",
                      "Ederson": "Ederson Santana de Moraes", "Luis Guilherme": "Luis Guilherme Lira dos Santos",
                      "Edson Álvarez": "Edson Álvarez Velázquez", "Emerson": "Emerson Palmieri dos Santos",
                      "Emile Smith-Rowe": "Emile Smith Rowe", "Emiliano Buendía": "Emiliano Buendía Stati",
                      "Emiliano Martinez": "Emiliano Martínez Romero", "Estupiñán": "Pervis Estupiñán",
                      "Fabinho": "Fabio Henrique Tavares", "Jaden Philogene-Bidace": "Jaden Philogene",
                      "Fred": "Frederico Rodrigues de Paula Santos", "Fábio Vieira": "Fábio Ferreira Vieira",
                      "Gabriel": "Gabriel dos Santos Magalhães", "Gabriel Jesus": "Gabriel Fernando de Jesus",
                      "Gabriel Martinelli": "Gabriel Martinelli Silva", "Chadi Riad": "Chadi Riad Dnanou",
                      "Gonçalo Guedes": "Gonçalo Manuel Ganchinho Guedes", "Renato Veiga": "Renato Palma Veiga",
                      "Gustavo Scarpa": "Gustavo Henrique Furtado Scarpa", "Halil Dervisoglu": "Halil Dervişoğlu",
                      "Hamed Junior Traore": "Hamed Traorè", "Hee-Chan Hwang": "Hwang Hee-chan",
                      "Hugo Bueno": "Hugo Bueno López", "Ibrahim Sangare": "Ibrahim Sangaré",
                      "Igor Julio": "Igor Julio dos Santos de Paulo", "Wataru Endo": "Endo Wataru",
                      "Issa Kabore": "Issa Kaboré", "Kaoru Mitoma": "Mitoma Kaoru",
                      "Iyenoma Destiny Udogie": "Destiny Udogie", "Javier Manquillo": "Javier Manquillo Gaitán",
                      "Jefferson Lerma": "Jefferson Lerma Solís", "Jeremy Sarmiento": "Jeremy Sarmiento Morante",
                      "Joelinton": "Joelinton Cássio Apolinário de Lira", "Rodrigo Gomes": "Rodrigo Martins Gomes",
                      "Jonny": "Jonny Evans", "Morato": "Felipe Rodrigues da Silva",
                      "Jorginho": "Jorge Luiz Frello Filho", "Joseph Gomez": "Joe Gomez",
                      "Josko Gvardiol": "Joško Gvardiol", "José Sá": "José Malheiro de Sá",
                      "João Gomes": "João Victor Gomes da Silva", "Jesper Lindstrom": "Jesper Lindstrøm",
                      "João Pedro": "João Pedro Junqueira de Jesus", "Jéremy Doku": "Jérémy Doku",
                      "Kaine Hayden": "Kaine Kesler-Hayden", "Kepa": "Kepa Arrizabalaga",
                      "Lucas Paquetá": "Lucas Tolentino Coelho de Lima", "Boubakary Soumare": "Boubakary Soumaré",
                      "Mads Roerslev": "Mads Roerslev Rasmussen", "Marc Cucurella": "Marc Cucurella Saseta",
                      "Marquinhos": "Marcus Oliveira Alencar", "Martin Odegaard": "Martin Ødegaard",
                      "Mateo Kovacic": "Mateo Kovačić", "Matheus Cunha": "Matheus Santos Carneiro Da Cunha",
                      "Matheus França": "Matheus França de Oliveira", "Matheus Nunes": "Matheus Luiz Nunes",
                      "Matthew Cash": "Matty Cash", "Carlos Vinicius": "Carlos Vinícius Alves Morais",
                      "Miguel Almirón": "Miguel Almirón Rejala", "Moisés Caicedo": "Moisés Caicedo Corozo",
                      "Murillo": "Murillo Santiago Costa dos Santos", "Ismaila Sarr": "Ismaïla Sarr",
                      "Naif Aguerd": "Nayef Aguerd", "Neto": "Norberto Murara Neto",
                      "Nélson Semedo": "Nélson Cabral Semedo", "William Smallbone": "Will Smallbone",
                      "Odisseas Vlachodimos": "Odysseas Vlachodimos",
                      "Pape Sarr": "Pape Matar Sarr",  "Mateus Fernandes": "Mateus Gonçalo Espanha Fernandes",
                      "Pedro Neto": "Pedro Lomba Neto", "Evanilson": "Francisco Evanilson de Lima Barbosa",
                      "Rayan Ait Nouri": "Rayan Aït-Nouri",
                      "Richarlison": "Richarlison de Andrade",
                      "Rodrigo": "Rodrigo Bentancur", "Rodrigo Muniz": "Rodrigo Muniz Carvalho",
                      "Romeo Lavia": "Roméo Lavia",
                      "Rúben Dias": "Rúben Gato Alves Dias", "Sasa Lukic": "Saša Lukić", "Sergi Canos": "Sergi Canós Tenés",
                      "Son Heung-Min": "Son Heung-min", "Tetê": "Kenny Tete",
                      "Tomas Soucek": "Tomáš Souček", "Toti": "Toti António Gomes",
                      "Valentino Livramento": "Tino Livramento",
                      "Vladimir Coufal": "Vladimír Coufal",
                      "Yehor Yarmolyuk": "Yehor Yarmoliuk", "Ricardo Pereira": "Ricardo Barbosa Pereira",
                      "Youssef Chermiti": "Youssef Ramalho Chermiti", "Zanka": "Mathias Jorgensen",
                      "Alisson": "Alisson Ramses Becker", "Jorge Cuenca": "Jorge Cuenca Barreno",
                      "Omari Hutchinson": "Omari Giraud-Hutchinson", "Joe Ayodele-Aribo": "Joe Aribo",
                      "Julián Araujo": "Julián Araujo Zúñiga", "Seamus Coleman": "Séamus Coleman",
                      "André": "André Trindade da Costa Neto"}


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
                raise Exception("2 players with the same name! " + player_name)

            if previous_players is None or player_name in previous_players:
                PIDs[player_name] = {'id': i, 'web_name': row['web_name'], 'first_name': row['first_name'],
                                     'last_name': row['second_name'], 'team': teams[int(row['team'])]['short_name'],
                                     'position': player_position}
                master_data_set.append(player)

    if USE_UNDERSTAT:
        load_understat()
    else:
        get_points(STARTING_SEASON)


def load_understat():
    global PIDs
    understat_players = os.listdir(f"../Fantasy-Premier-League/data/{CURRENT_SEASON}/understat")
    understat_players = [player for player in understat_players if not player.startswith("understat")]

    for i, understat_player in enumerate(understat_players):
        name = ' '.join(understat_player.split("_")[:-1]).replace('&#039;', '\'')

        if name in old_players:
            continue

        if name in understat_name_map:
            name = understat_name_map[name]

        if name not in PIDs:
            raise Exception(f"Didn't find a player with the name {name}")

        PIDs[name]['understat'] = {}

        with open(f"../Fantasy-Premier-League/data/{CURRENT_SEASON}/understat/{understat_player}") as understat_file:
            understat_reader = csv.DictReader(understat_file)

            for player_element in understat_reader:
                PIDs[name]['understat'][player_element['date']] = player_element

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
        fixture_to_team = {}

        for fixture in fixture_reader:
            fixture_to_difficulty[int(fixture['id'])] = {'h': int(fixture['team_h_difficulty']),
                                                         'a': int(fixture['team_a_difficulty'])}
            fixture_to_team[int(fixture['id'])] = {'h': teams[int(fixture['team_h'])]['short_name'],
                                                   'a': teams[int(fixture['team_a'])]['short_name']}

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
        case "2024-25":
            game_round = 314

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
                    print(f"No understats for {name} for {fixture_date}")
                    continue

                points_data_set[element_object['id']][f"GW{game_round}"] = {'diff': diff,
                                                                            'points': int(gw_element['total_points']),
                                                                            'team': opp_team}

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
            get_points("2024-25")
        case "2024-25":
            write_points_data()


def write_points_data():
    global points_data_set
    with open(f"./datasets/{CURRENT_SEASON}/dataset{CURRENT_GAME_WEEK}{"Challenge" if CHALLENGE_TEAM else ""}.json", 'w') as dataset_file:
        json.dump(points_data_set, dataset_file, ensure_ascii=False, indent=4)


def get_dataset():
    global points_data_set, master_data_set, PIDs, teams
    PIDs = {}
    teams = {}
    points_data_set = {}
    master_data_set = [
    ["First Name", "Surname", "Web Name", "Position", "GKP", "DEF", "MID", "FWD", "Team", *TEAMS, "Cost", "ID", "ARIMA",
     "LSTM", "FOREST", "PP", "NEXT", "Health", "PREV", "Selected"]]
    get_teams()
    return points_data_set, master_data_set
