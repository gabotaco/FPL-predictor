const compSeasonID = 489

const gameInformation = require("./game_information")
const playerInformation = require("./player_information")

let teams = null;
const players = {}
const picked = {}

function init() {
    logIn()
}

function logIn() {
    playerInformation.logIn().then(() => {
        getTeamIdToName();
    })
}

function getTeamIdToName() {
    gameInformation.getTeamInformation().then(newTeams => {
        teams = newTeams;
        getPlayerIdToName();
    })
}

function getPlayerIdToName() {
    playerInformation.request.get(`https://fantasy.premierleague.com/api/bootstrap-static/`, function (err, response) {
        if (err) throw err;
        const elements = JSON.parse(response.body).elements
        elements.forEach(player => {
            players[player.id] = {
                firstName: player.first_name,
                lastName: player.second_name,
                webName: player.web_name,
                team: player.team,
                position: gameInformation.POSITIONS[player.element_type],
                points: player.event_points
            }
        });
        getGWPlayers()
    })
}

function getGWPlayers() {
    playerInformation.request.get(`https://fantasy.premierleague.com/api/my-team/${playerInformation.TEAM.id}/`, function (err, response) {
        if (err) throw err;
        if (response.body == `"The game is being updated."`) {
            console.log(`The game is currently being updated. Rerun when it's done.`);
            return;
        }
        const res = JSON.parse(response.body)
        if (res.detail == "Not found.") {
            console.log(`Provided team is not of the logged in user.`);
            return;
        } else if (res.detail == "Authentication credentials were not provided.") {
            console.log(`Invalid login.`);
            return;
        }
        res.picks.forEach(player => {
            let element = players[player.element]
            element.teamPosition = player.position;
            element.isCaptain = player.is_captain
            element.isVice = player.is_vice_captain
            if (!picked[element.team]) picked[element.team] = []
            picked[element.team].push(element);
        });
        getPlayerNumbers();
    })
}

function getPlayerNumsOnTeam(index) {
    const team = Object.keys(picked)[index]
    if (!team) {
        getFixtures()
        return;
    }
    let found = 0;
    playerInformation.request.get({
        url: `https://footballapi.pulselive.com/football/teams/${teams[team].pulse}/compseasons/${compSeasonID}/staff`,
        headers: {
            "Origin": "https://www.premierleague.com"
        }
    }, function (err, response, body) {
        const res = JSON.parse(body)
        res.players.forEach(player => {
            const playerName = `${player.name.first.normalize("NFD").replace(/[\u0300-\u036f]/g, "")}${player.name.middle ? player.name.middle.normalize("NFD").replace(/[\u0300-\u036f]/g, "") : ""}${player.name.last.normalize("NFD").replace(/[\u0300-\u036f]/g, "")}`.replace(/ /g, "")
            picked[team].forEach((pick, i) => {
                const pickPlayerName = `${pick.firstName.normalize("NFD").replace(/[\u0300-\u036f]/g, "")}${pick.lastName.normalize("NFD").replace(/[\u0300-\u036f]/g, "")}`.replace(/ /g, "")
                if ((playerName.includes(pick.firstName.normalize("NFD").replace(/[\u0300-\u036f]/g, "").replace(/ /g, "")) && playerName.includes(pick.lastName.normalize("NFD").replace(/[\u0300-\u036f]/g, "").replace(/ /g, ""))) || (pickPlayerName.includes(player.name.first.normalize("NFD").replace(/[\u0300-\u036f]/g, "").replace(/ /g, "")) && pickPlayerName.includes(player.name.last.normalize("NFD").replace(/[\u0300-\u036f]/g, "").replace(/ /g, "")))) {
                    found++;

                    picked[team][i].num = player.info.shirtNum
                    picked[team][i].pulse_id = player.id
                }
            });
        });
        if (found < picked[team].length) {
            picked[team].forEach((pick, i) => {
                if (!pick.num) {
                    console.log(`Unable to match ${pick.firstName} : ${pick.lastName}`);
                    picked[team][i].num = "#"
                    picked[team][i].pulse_id = false;
                }
            });
        }
        getPlayerNumsOnTeam(index + 1)
    })

}

function getPlayerNumbers() {
    getPlayerNumsOnTeam(0)

}

function getFixtures() {
    playerInformation.request.get(`https://fantasy.premierleague.com/api/fixtures/?event=${gameInformation.CURRENT_GAME_WEEK}`, function (err, response) {
        if (err) throw err;
        const fixtures = JSON.parse(response.body)
        const weekday = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]
        const ONE_HOUR = 1 * 60 * 60 * 1000
        function processFixture(index) {
            const fixture = fixtures[index]
            if (!fixture) return;
            const when = new Date(fixture.kickoff_time)
            console.log(`${playerInformation.TEAM.name} has ${(picked[fixture.team_a] ? picked[fixture.team_a].length : 0) + (picked[fixture.team_h] ? picked[fixture.team_h].length : 0)} ${((picked[fixture.team_a] ? picked[fixture.team_a].length : 0) + (picked[fixture.team_h] ? picked[fixture.team_h].length : 0)) == 1 ? "player" : "players"} in the ${teams[fixture.team_h].longName} (${teams[fixture.team_h].shortName}) VS ${teams[fixture.team_a].longName} (${teams[fixture.team_a].shortName}) game at ${when.getHours() % 12 == 0 ? 12 : when.getHours() % 12}:${when.getMinutes() == 0 ? "00" : when.getMinutes()} on ${weekday[when.getDay()]}`);
            if (when <= new Date().getTime() + ONE_HOUR) {
                playerInformation.request.get({
                    url: `https://footballapi.pulselive.com/football/fixtures/${fixture.pulse_id}`,
                    headers: {
                        "Origin": "https://www.premierleague.com"
                    }
                }, function (err, response) {
                    if (err) throw err;
                    const line_up = JSON.parse(response.body).teamLists
                    if (picked[fixture.team_h]) {
                        console.log("     Home Players:");
                        picked[fixture.team_h].forEach(element => {
                            if (!element.pulse_id) {
                                console.log(`                    ${element.teamPosition >= 12 ? (element.teamPosition == 12 ? " SUB" : ` SUB ${element.teamPosition - 12}`) : ""} ${element.position}: #${element.num} ${element.isCaptain ? "CAPTAIN" : element.isVice ? "VICE CAPTAIN" : ""} ${element.webName} (${teams[fixture.team_h].shortName}). ${fixture.finished ? `Got ${element.points} ${element.points == 1 ? "point" : "points"}` : "Playing: UNKNOWN"}`.replace(/  /g, " "));
                            } else {
                                let foundPlayer = false;
                                line_up[0].lineup.forEach(starter => {
                                    if (starter.id == element.pulse_id) {
                                        foundPlayer = true;
                                        console.log(`                    ${element.teamPosition >= 12 ? (element.teamPosition == 12 ? " SUB" : ` SUB ${element.teamPosition - 12}`) : ""} ${element.position}: #${starter.matchShirtNumber} ${element.isCaptain ? "CAPTAIN" : element.isVice ? "VICE CAPTAIN" : ""} ${element.webName} (${teams[fixture.team_h].shortName}). ${fixture.finished ? `Got ${element.points} ${element.points == 1 ? "point" : "points"}` : "Playing: STARTING"}`.replace(/  /g, " "));
                                    }
                                });
                                line_up[0].substitutes.forEach((sub) => {
                                    if (sub.id == element.pulse_id) {
                                        foundPlayer = true;
                                        console.log(`                    ${element.teamPosition >= 12 ? (element.teamPosition == 12 ? " SUB" : ` SUB ${element.teamPosition - 12}`) : ""} ${element.position}: #${sub.matchShirtNumber} ${element.isCaptain ? "CAPTAIN" : element.isVice ? "VICE CAPTAIN" : ""} ${element.webName} (${teams[fixture.team_h].shortName}). ${fixture.finished ? `Got ${element.points} ${element.points == 1 ? "point" : "points"}` : "Playing: Substitute"}`.replace(/  /g, " "));
                                    }
                                })
                                if (foundPlayer) return;
                                else {
                                    console.log(`                    ${element.teamPosition >= 12 ? (element.teamPosition == 12 ? " SUB" : ` SUB ${element.teamPosition - 12}`) : ""} ${element.position}: #${element.num} ${element.isCaptain ? "CAPTAIN" : element.isVice ? "VICE CAPTAIN" : ""} ${element.webName} (${teams[fixture.team_h].shortName}). ${fixture.finished ? `Got ${element.points} ${element.points == 1 ? "point" : "points"}` : "Playing: NO"}`.replace(/  /g, " "));
                                }
                            }
                        });
                    }
                    if (picked[fixture.team_a]) {
                        console.log("     Away Players:");
                        picked[fixture.team_a].forEach(element => {
                            if (!element.pulse_id) {
                                console.log(`                    ${element.teamPosition >= 12 ? (element.teamPosition == 12 ? " SUB" : ` SUB ${element.teamPosition - 12}`) : ""} ${element.position}: #${element.num} ${element.isCaptain ? "CAPTAIN" : element.isVice ? "VICE CAPTAIN" : ""} ${element.webName} (${teams[fixture.team_a].shortName}). ${fixture.finished ? `Got ${element.points} ${element.points == 1 ? "point" : "points"}` : "Playing: UNKNOWN"}`.replace(/  /g, " "));
                            } else {
                                let foundPlayer = false;
                                line_up[1].lineup.forEach(starter => {
                                    if (starter.id == element.pulse_id) {
                                        foundPlayer = true;
                                        console.log(`                    ${element.teamPosition >= 12 ? (element.teamPosition == 12 ? " SUB" : ` SUB ${starter.teamPosition - 12}`) : ""} ${element.position}: #${starter.matchShirtNumber} ${element.isCaptain ? "CAPTAIN" : element.isVice ? "VICE CAPTAIN" : ""} ${element.webName} (${teams[fixture.team_a].shortName}). ${fixture.finished ? `Got ${element.points} ${element.points == 1 ? "point" : "points"}` : "Playing: STARTING"}`.replace(/  /g, " "));
                                    }
                                });
                                line_up[1].substitutes.forEach((sub) => {
                                    if (sub.id == element.pulse_id) {
                                        foundPlayer = true;
                                        console.log(`                    ${element.teamPosition >= 12 ? (element.teamPosition == 12 ? " SUB" : ` SUB ${sub.teamPosition - 12}`) : ""} ${element.position}: #${sub.matchShirtNumber} ${element.isCaptain ? "CAPTAIN" : element.isVice ? "VICE CAPTAIN" : ""} ${element.webName} (${teams[fixture.team_a].shortName}). ${fixture.finished ? `Got ${element.points} ${element.points == 1 ? "point" : "points"}` : "Playing: Substitute"}`.replace(/  /g, " "));
                                    }
                                })
                                if (foundPlayer) return;
                                else {
                                    console.log(`                    ${element.teamPosition >= 12 ? (element.teamPosition == 12 ? " SUB" : ` SUB ${element.teamPosition - 12}`) : ""} ${element.position}: #${element.num} ${element.isCaptain ? "CAPTAIN" : element.isVice ? "VICE CAPTAIN" : ""} ${element.webName} (${teams[fixture.team_a].shortName}). ${fixture.finished ? `Got ${element.points} ${element.points == 1 ? "point" : "points"}` : "Playing: NO"}`.replace(/  /g, " "));
                                }
                            }
                        });
                    }
                    processFixture(index + 1)
                })
            } else {
                if (picked[fixture.team_h]) {
                    console.log("     Home Players:");
                    picked[fixture.team_h].forEach(element => {
                        console.log(`                    ${element.teamPosition >= 12 ? (element.teamPosition == 12 ? " SUB" : ` SUB ${element.teamPosition - 12}`) : ""} ${element.position}: #${element.num} ${element.isCaptain ? "CAPTAIN" : element.isVice ? "VICE CAPTAIN" : ""} ${element.webName} (${teams[fixture.team_h].shortName}). ${fixture.finished ? `Got ${element.points} ${element.points == 1 ? "point" : "points"}` : ""}`.replace(/  /g, " "));
                    });
                }
                if (picked[fixture.team_a]) {
                    console.log("     Away Players:");
                    picked[fixture.team_a].forEach(element => {
                        console.log(`                    ${element.teamPosition >= 12 ? (element.teamPosition == 12 ? " SUB" : ` SUB ${element.teamPosition - 12}`) : ""} ${element.position}: #${element.num} ${element.isCaptain ? "CAPTAIN" : element.isVice ? "VICE CAPTAIN" : ""} ${element.webName} (${teams[fixture.team_a].shortName}). ${fixture.finished ? `Got ${element.points} ${element.points == 1 ? "point" : "points"}` : ""}`.replace(/  /g, " "));
                    });
                }
                processFixture(index + 1)
            }
        }
        processFixture(0)
    })
}

init()