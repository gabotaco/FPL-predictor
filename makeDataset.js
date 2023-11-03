const gameInformation = require("./game_information");
const fs = require('fs')

const STARTING_SEASON = "2018-19"
const NO_NEW_PLAYERS = false;

const PIDs = {}
let teams = {}
let callback;
const pointsDataSet = {};
const masterDataSet = [
    ["First Name", "Surname", "Web Name", "Position", "GKP", "DEF", "MID", "FWD", "Team", ...gameInformation.TEAMS, "Cost", "ID", "ARIMA", "LSTM", "PPG", "NEXT", "PREV", "Selected"]
];

function getTeams() {
    gameInformation.getTeamInformation().then(newTeams => {
        teams = newTeams;
        if (NO_NEW_PLAYERS) {
            getPreviousThenCurrentPlayers();
        } else {
            getCurrentPlayers(null);
        }
    })
}

function getPreviousThenCurrentPlayers() {
    fs.readFile(`./data/${gameInformation.PREVIOUS_SEASON}/players_raw.csv`, 'utf8', function (err, data) {
        const previousPlayers = [];

        if (err) throw err;

        const rows = data.split(/\r?\n/)
        const header = rows[0].split(",")
        const first_name_index = header.indexOf("first_name")
        const surname_index = header.indexOf("second_name")
        rows.forEach((row, i) => {
            if (i == 0) return;
            row = row.split(",")

            if (previousPlayers.includes(`${row[first_name_index]} ${row[surname_index]}`)) throw '2 players have the same name!';

            previousPlayers.push(`${row[first_name_index]} ${row[surname_index]}`);
        });

        getCurrentPlayers(previousPlayers)
    });
}

function getCurrentPlayers(previousPlayers) {
    fs.readFile(`./data/${gameInformation.CURRENT_SEASON}/players_raw.csv`, 'utf8', function (err, data) {
        if (err) throw err;
        const rows = data.split(/\r?\n/)
        const header = rows[0].split(",")
        const first_name_index = header.indexOf("first_name")
        const surname_index = header.indexOf("second_name")
        const position = header.indexOf("element_type")
        const team = header.indexOf("team")
        const cost = header.indexOf("now_cost");
        const webname_index = header.indexOf("web_name")
        rows.forEach((row, i) => {
            if (i == 0) return;
            row = row.replace(/\".*\"/, "").split(",")

            const player = [row[first_name_index], row[surname_index], row[webname_index], gameInformation.POSITIONS[row[position]], gameInformation.POSITIONS[row[position]] == "GKP" ? 1 : 0, gameInformation.POSITIONS[row[position]] == "DEF" ? 1 : 0, gameInformation.POSITIONS[row[position]] == "MID" ? 1 : 0, gameInformation.POSITIONS[row[position]] == "FWD" ? 1 : 0, teams[row[team]].shortName]
            for (const teamName of gameInformation.TEAMS) {
                if (teams[row[team]].shortName == teamName) {
                    player.push(1);
                } else {
                    player.push(0);
                }
            }
            player.push(parseInt(row[cost]) / 10);
            player.push(i);

            if (PIDs[`${row[first_name_index]} ${row[surname_index]}`]) throw '2 players with the same name!';

            if (previousPlayers && !previousPlayers.includes(`${row[first_name_index]} ${row[surname_index]}`)) {
                return;
            }

            PIDs[`${row[first_name_index]} ${row[surname_index]}`] = {
                "id": i,
                "web_name": row[webname_index],
                "first_name": row[first_name_index],
                "last_name": row[surname_index],
                "team": teams[row[team]].shortName
            }
            masterDataSet.push(player)
        });
        getPoints(STARTING_SEASON)
    })
}

function getPoints(year) {
    fs.readFile(`./data/${year}/player_idlist.csv`, 'utf8', function (err, data) {
        if (err) throw err;
        const rows = data.split(/\r?\n/)
        const header = rows[0].split(",")
        const first_name_index = header.indexOf("first_name")
        const surname_index = header.indexOf("second_name")

        const elementsToUse = {}
        const usedPlayers = {}
        rows.forEach((row, i) => {
            if (i == 0) return;
            const playerID = row.split(",")
            if (PIDs[`${playerID[first_name_index]} ${playerID[surname_index]}`]) {
                elementsToUse[`${playerID[first_name_index]} ${playerID[surname_index]}`] = PIDs[`${playerID[first_name_index]} ${playerID[surname_index]}`];
                usedPlayers[PIDs[`${playerID[first_name_index]} ${playerID[surname_index]}`].id] = true;
            }
        });

        fs.readFile(`./data/${year}/fixtures.csv`, 'utf8', function (err, data) {
            if (err) throw err;
            const rows = data.split(/\r?\n/)
            const header = rows[0].split(",");
            const id_index = header.indexOf("id");
            const h_diff = header.indexOf("team_h_difficulty");
            const a_diff = header.indexOf("team_a_difficulty");

            const fixtureToDifficulty = {};

            rows.forEach((row, i) => {
                if (i == 0) return;
                const fixture = row.replace(/\".*\"/, "").split(",");
                fixtureToDifficulty[fixture[id_index]] = {
                    "h": parseInt(fixture[h_diff]),
                    "a": parseInt(fixture[a_diff])
                }
            })
    
            fs.readdir(`./data/${year}/gws/`, function (err, gws) {
                if (err) throw err;
                gws.sort((a, b) => {
                    return parseInt(a.replace("gw", "")) - parseInt(b.replace("gw", ""))
                })
                switch (year) {
                    case "2016-17":
                        addPlayer(year, gws, 0, 1)
                        break;
                    case "2017-18":
                        addPlayer(year, gws, 0, 39)
                        break;
                    case "2018-19":
                        addPlayer(year, gws, 0, 77)
                        break;
                    case "2019-20":
                        addPlayer(year, gws, 0, 115)
                        break;
                    case "2020-21":
                        addPlayer(year, gws, 0, 162)
                        break;
                    case "2021-22":
                        addPlayer(year, gws, 0, 199)
                        break;
                    case "2022-23":
                        addPlayer(year, gws, 0, 237)
                        break;
                    case "2023-24":
                        addPlayer(year, gws, 0, 273)
                        break;
                }
            })
    
            function addPlayer(year, gws, index, round) {
                const gw = gws[index]
                if (!gw) {
                    switch (year) {
                        case "2016-17":
                            getPoints("2017-18")
                            break;
                        case "2017-18":
                            getPoints("2018-19")
                            break;
                        case "2018-19":
                            getPoints("2019-20")
                            break;
                        case "2019-20":
                            getPoints("2020-21")
                            break;
                        case "2020-21":
                            getPoints("2021-22")
                            break;
                        case "2021-22":
                            getPoints("2022-23")
                            break;
                        case "2022-23":
                            getPoints("2023-24")
                            break;
                        case "2023-24":
                            cleanPointsData()
                            break;
                    }
                    return;
                }
                if (!gw.startsWith("gw")) {
                    addPlayer(year, gws, index + 1, round)
                    return;
                }
 
                fs.readFile(`./data/${year}/gws/${gw}`, 'utf8', function (err, data) {
                    if (err) throw err;
                    const rows = data.split(/\r?\n/)
                    const header = rows[0].split(",")
                    const pointIndex = header.indexOf("total_points")
                    const fixtureIndex = header.indexOf("fixture")
                    const homeIndex = header.indexOf("was_home")
                    const minutesIndex = header.indexOf("minutes")
                    const nameIndex = header.indexOf("name")
    
                    rows.forEach((row, i) => {
                        if (i == 0) return;
                        const element = row.split(",")
                        const elementObject = elementsToUse[element[nameIndex]]
    
                        if (!elementObject) return;
                        if (parseInt(element[minutesIndex]) == 0) return;
                        const dataSetObject = pointsDataSet[elementObject.id]
                        if (!dataSetObject) {
                            pointsDataSet[elementObject.id] = {
                                "first_name": elementObject.first_name,
                                "last_name": elementObject.last_name,
                                "name": elementObject.web_name,
                                "team": elementObject.team,
                                "id": elementObject.id
                            }
                        }

                        const diff = fixtureToDifficulty[element[fixtureIndex]][element[homeIndex] == "True" ? 'h' : 'a']
                        if (!diff) {
                            throw "Couldn't find diff"
                        }

                        pointsDataSet[elementObject.id][`GW${round}`] = {
                            "diff": diff,
                            "points": parseInt(element[pointIndex])
                        }
                    });
    
                    addPlayer(year, gws, index + 1, round + 1)
                })
            }
        })
    })
}

function cleanPointsData() {
    fs.writeFile(`./datasets/${gameInformation.CURRENT_SEASON}/dataset${gameInformation.CURRENT_GAME_WEEK}.json`, JSON.stringify(pointsDataSet), function (err) {
        if (err) throw err
        callback();
    });
}

function getDataset() {
    return new Promise((resolve, reject) => {
        callback = () => {
            resolve({"points": pointsDataSet, 
                    "master": masterDataSet});
        };
        getTeams();
    })
}

module.exports = {getDataset}