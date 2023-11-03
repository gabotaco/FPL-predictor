const fs = require("fs/promises");

const TEAMS = ["ARS", "AVL", "BOU", "BRE", "BHA", "BUR", "CHE", "CRY", "EVE", "FUL", "LIV", "LUT", "MCI", "MUN", "NEW", "NFO", "SHU", "TOT", "WHU", "WOL"];
const CURRENT_GAME_WEEK = 11;
const CURRENT_SEASON_BEGINNING_ROUND = 273;
const SEASON_LENGTH = 36;
const CURRENT_SEASON = "2023-24";
const PREVIOUS_SEASON = "2022-23";
const MIN_GAMES = 3;
const MIN_SEASON_PPG = 2;
const MIN_SEASON_GAME_PERC = 0.7;
const POSITIONS = {
    1: "GKP",
    2: "DEF",
    3: "MID",
    4: "FWD"
}

function getTeamInformation() {
    const teams = {};
    return fs.readFile(`./data/${CURRENT_SEASON}/teams.csv`, 'utf8').then(data => {
        const rows = data.split(/\r?\n/)
        const header = rows[0].split(",")
        const idIndex = header.indexOf("id")
        const shortNameIndex = header.indexOf("short_name")
        const nameIndex = header.indexOf("name")
        const pulseIdIndex = header.indexOf("pulse_id")
        rows.forEach((row, i) => {
            if (i == 0) return;
            const team = row.split(",")
            teams[team[idIndex]] = {
                "shortName": team[shortNameIndex],
                "longName": team[nameIndex],
                "pulse": team[pulseIdIndex]
            }
        });

        return teams;
    }).catch(err => {
        throw err;
    })
}

module.exports = { MIN_GAMES, PREVIOUS_SEASON, CURRENT_GAME_WEEK, CURRENT_SEASON_BEGINNING_ROUND, CURRENT_SEASON, POSITIONS, getTeamInformation, MIN_SEASON_PPG, MIN_SEASON_GAME_PERC, TEAMS, SEASON_LENGTH }