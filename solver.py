from gekko import GEKKO


def make_team_list(list_data, team_names, header, predict_by_weeks, transfer_cost, free_transfers, team_worth,  gkps,
                   defs, mids, fwds, total_players, max_per_team):
    def convert_player_data(player):
        player_data = {
            "first_name": player[header.index('First Name')],
            "last_name": player[header.index('Surname')],
            "pp": player[header.index("PP")],
            "next": player[header.index("NEXT")],
            "health": player[header.index("Health")],
            "prev": player[header.index("PREV")],
            "cost": player[header.index("Cost")],
            "gkp": player[header.index("GKP")],
            "def": player[header.index("DEF")],
            "mid": player[header.index("MID")],
            "fwd": player[header.index("FWD")],
        }

        for team in team_names:
            team_index = header.index(team)
            player_data[team] = player[team_index]

        return player_data

    return make_team(list(map(convert_player_data, list_data)), predict_by_weeks, transfer_cost, free_transfers,
                     team_worth, team_names, gkps, defs, mids, fwds, total_players, max_per_team)


def make_team(data, predict_by_weeks, transfer_cost, free_transfers, max_cost, team_names, gkps, defs, mids, fwds,
              total_players, max_per_team):
    def apply_player_health(player):
        player['pp'] *= player['health']
        return player

    players = list(map(apply_player_health, data))

    m = GEKKO(remote=False)
    m.options.SOLVER = 1

    x = [m.Var(lb=0, ub=1, integer=True) for _ in players]

    points_column = 'pp' if predict_by_weeks > 1 else 'next'
    if transfer_cost == 0 or transfer_cost is None or free_transfers >= total_players or free_transfers is None:
        m.Maximize(sum(x[i] * players[i][points_column] for i in range(len(players))))
    else:
        m.Maximize(sum(x[i] * players[i][points_column] for i in range(len(players)))
                   - (predict_by_weeks * transfer_cost * m.max2(0,
                                                                sum(x[i] * (1 - players[i]['prev'])
                                                                    for i in range(len(players)))
                                                                - free_transfers)))

    if max_cost is not None:
        m.Equation(sum(x[i] * players[i]['cost'] for i in range(len(players))) <= max_cost)

    min_gkp, max_gkp = gkps
    if min_gkp == max_gkp:
        m.Equation(sum(x[i] * players[i]['gkp'] for i in range(len(players))) == max_gkp)
    else:
        m.Equation(sum(x[i] * players[i]['gkp'] for i in range(len(players))) >= min_gkp)
        m.Equation(sum(x[i] * players[i]['gkp'] for i in range(len(players))) <= max_gkp)
    min_def, max_def = defs
    if min_def == max_def:
        m.Equation(sum(x[i] * players[i]['def'] for i in range(len(players))) == max_def)
    else:
        m.Equation(sum(x[i] * players[i]['def'] for i in range(len(players))) >= min_def)
        m.Equation(sum(x[i] * players[i]['def'] for i in range(len(players))) <= max_def)
    min_mid, max_mid = mids
    if min_mid == max_mid:
        m.Equation(sum(x[i] * players[i]['mid'] for i in range(len(players))) == max_mid)
    else:
        m.Equation(sum(x[i] * players[i]['mid'] for i in range(len(players))) >= min_mid)
        m.Equation(sum(x[i] * players[i]['mid'] for i in range(len(players))) <= max_mid)
    min_fwd, max_fwd = fwds
    if min_fwd == max_fwd:
        m.Equation(sum(x[i] * players[i]['fwd'] for i in range(len(players))) == max_fwd)
    else:
        m.Equation(sum(x[i] * players[i]['fwd'] for i in range(len(players))) >= min_fwd)
        m.Equation(sum(x[i] * players[i]['fwd'] for i in range(len(players))) <= max_fwd)

    m.Equation(sum(x[i] for i in range(len(players))) == total_players)

    if max_per_team is not None and max_per_team < total_players:
        for team in team_names:
            m.Equation(sum(x[i] * players[i][team] if team in players[i] else 0 for i in range(len(players))) <=
                       max_per_team)

    m.solve(disp=False)

    return [f"{players[i]['first_name']} {players[i]['last_name']}" for i in range(len(players)) if x[i].value[0] == 1]


def calibrate_player(arima, lstm, actual_points):
    m = GEKKO(remote=False)
    arima_v = m.Var(value=0, lb=0)
    lstm_v = m.Var(value=0, lb=0)

    m.Minimize((((arima * arima_v) + (lstm * lstm_v)) - actual_points) ** 2)

    m.solve(disp=False)

    return arima_v.value[0], lstm_v.value[0]
