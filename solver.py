from gekko import GEKKO

from game_information import TEAM_WORTH, FREE_TRANSFERS, PREDICT_BY_WEEKS, TRANSFER_COST, TEAMS

from dataset import master_data_set as header

MAX_GKP = 2
MAX_DEF = 5
MAX_MID = 5
MAX_FWD = 3
TOTAL_PLAYERS = MAX_GKP + MAX_DEF + MAX_MID + MAX_FWD

MAX_PER_TEAM = 3

COST = header[0].index("Cost")
PP = header[0].index("PP")
PREV = header[0].index("PREV")
GKP = header[0].index("GKP")
DEF = header[0].index("DEF")
MID = header[0].index("MID")
FWD = header[0].index("FWD")
HEALTH = header[0].index("Health")


def make_team(data):
    def apply_player_health(player):
        player[PP] *= player[HEALTH]
        return player

    players = list(map(apply_player_health, data))

    m = GEKKO(remote=False)
    m.options.SOLVER = 1

    x = [m.Var(lb=0, ub=1, integer=True) for _ in players]

    m.Maximize(sum(x[i] * players[i][PP] for i in range(len(players)))
               - (PREDICT_BY_WEEKS * TRANSFER_COST * m.max2(0,
                                                            sum(x[i] * (1 - players[i][PREV])
                                                                for i in range(len(players)))
                                                            - FREE_TRANSFERS)))

    m.Equation(sum(x[i] * players[i][COST] for i in range(len(players))) <= TEAM_WORTH)

    m.Equation(sum(x[i] * players[i][GKP] for i in range(len(players))) == MAX_GKP)
    m.Equation(sum(x[i] * players[i][DEF] for i in range(len(players))) == MAX_DEF)
    m.Equation(sum(x[i] * players[i][MID] for i in range(len(players))) == MAX_MID)
    m.Equation(sum(x[i] * players[i][FWD] for i in range(len(players))) == MAX_FWD)

    for team in TEAMS:
        team_index = header[0].index(team)
        m.Equation(sum(x[i] * players[i][team_index] for i in range(len(players))) <= MAX_PER_TEAM)

    m.solve(disp=False)

    return [players[i] for i in range(len(players)) if x[i].value[0] == 1]


def make_calibration(players):
    m = GEKKO(remote=False)
    arima = m.Var(value=0, lb=0)
    lstm = m.Var(value=0, lb=0)
    forest = m.Var(value=0, lb=0)

    m.Minimize(sum((((players[i]['arima'] * arima)
                    + (players[i]['lstm'] * lstm)
                    + (players[i]['forest'] * forest))
                    - players[i]['actual_points']) ** 2 for i in range(len(players))))

    m.solve(disp=False)

    return arima.value[0], lstm.value[0], forest.value[0]


def calibrate_player(arima, lstm, forest, actual_points):
    m = GEKKO(remote=False)
    arima_v = m.Var(value=0, lb=0)
    lstm_v = m.Var(value=0, lb=0)
    forest_v = m.Var(value=0, lb=0)

    m.Minimize((((arima * arima_v) + (lstm * lstm_v) + (forest * forest_v)) - actual_points) ** 2)

    m.solve(disp=False)

    return arima_v.value[0], lstm_v.value[0], forest_v.value[0]
