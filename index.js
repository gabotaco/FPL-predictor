const fs = require("fs")
const ExcelJS = require('exceljs');
const neuralNetwork = require("./neuralNetwork")
const gameInformation = require("./game_information");
const datasetMaker = require('./makeDataset');

const TEAM_WORTH = 97.2 + 3.2;
const freeTransfers = 2;
const PREDICT_BY_WEEKS = 5;
const previousTeam = [
    "Mark Flekken Flekken", "André Onana Onana", // GKP
    "Micky van de Ven Van de Ven", "Pau Torres Pau", "Thiago Emiliano da Silva T.Silva", "Axel Disasi Disasi", "Kieran Trippier Trippier", // DEF
    "Jarrod Bowen Bowen", "Morgan Gibbs-White Gibbs-White", "Raheem Sterling Sterling", "Dejan Kulusevski Kulusevski", "Moussa Diaby Diaby", // MID
    "Erling Haaland Haaland", "Ollie Watkins Watkins", "Matheus Santos Carneiro Da Cunha Cunha" // FWD
];
const processAllPlayers = false;
const buggedPlayers = [];
const RATIOS = { // Last calibrated 10/26/2023
    "ARS": {
        "ARIMA": 0.451545234262846,
        "LSTM": 0.428357260073197
    },
    "AVL": {
        "ARIMA": 0.552701202630342,
        "LSTM": 0.550631115289244
    },
    "BOU": {
        "ARIMA": 0.344417344520579,
        "LSTM": 0.336785354765711
    },
    "BRE": {
        "ARIMA": 0.554909941474556,
        "LSTM": 0.569861354608904
    },
    "BHA": {
        "ARIMA": 0.449186454018497,
        "LSTM": 0.469534696573657
    },
    "BUR": {
        "ARIMA": 0,
        "LSTM": 0
    },
    "CHE": {
        "ARIMA": 0.538036386015151,
        "LSTM": 0.480280123799665
    },
    "CRY": {
        "ARIMA": 0.551053480708866,
        "LSTM": 0.485606212836427
    },
    "EVE": {
        "ARIMA": 0.45385676171936,
        "LSTM": 0.432442685857298
    },
    "FUL": {
        "ARIMA": 0.480811272310951,
        "LSTM": 0.393630554196992
    },
    "LIV": {
        "ARIMA": 0.44652955619295,
        "LSTM": 0.416499260066055
    },
    "LUT": {
        "ARIMA": 0,
        "LSTM": 0
    },
    "MCI": {
        "ARIMA": 0.387213192301701,
        "LSTM": 0.322800279929932
    },
    "MUN": {
        "ARIMA": 0.32750071257945,
        "LSTM": 0.329711169104903
    },
    "NEW": {
        "ARIMA": 0.520001575258516,
        "LSTM": 0.398896595641724
    },
    "NFO": {
        "ARIMA": 0.457982864643449,
        "LSTM": 0.394694998361326
    },
    "SHU": {
        "ARIMA": 0,
        "LSTM": 0
    },
    "TOT": {
        "ARIMA": 0.55531974481879,
        "LSTM": 0.511211253601715
    },
    "WHU": {
        "ARIMA": 0.451855538594391,
        "LSTM": 0.517609285484624
    },
    "WOL": {
        "ARIMA": 0.548737649806623,
        "LSTM": 0.575798966120245
    }
}
const HIDDEN_COLUMNS = ["GKP", "DEF", "MID", "FWD", ...gameInformation.TEAMS, "ID", "ARIMA", "LSTM"];

let masterDataSet;
const deletedMembers = []
let pointsDataSet;
const predictBy = {}
let ALPHABET = [];

function init() {
    for (const team of gameInformation.TEAMS) {
        predictBy[team] = {
            "games": [],
            "next": 0
        }
    }

    ALPHABET = "ABCDEFGHIJKLMNOPQRSTUVWXYZ".split("");
    for (const letter of "ABCDEFGHIJKLMNOPQRSTUVWXYZ".split("")) {
        ALPHABET.push(`A${letter}`);
    }

    datasetMaker.getDataset().then(datasets => {
        pointsDataSet = datasets.points;
        masterDataSet = datasets.master;
        getPredictBy();
    })
}

function getPredictBy() {
    gameInformation.getTeamInformation().then(newTeams => {
        console.log('newTeams', newTeams)
        fs.readFile(`./data/${gameInformation.CURRENT_SEASON}/fixtures.csv`, 'utf8', function (err, data) {
            if (err) throw err;
            let rows = data.split(/\r?\n/)
            const header = rows[0].split(",");
            const eventIndex = header.indexOf("event");
            const hteamIndex = header.indexOf("team_h");
            const ateamIndex = header.indexOf("team_a");
            const hTeamDifficultyIndex = header.indexOf("team_h_difficulty");
            const aTeamDifficultyIndex = header.indexOf("team_a_difficulty");

            rows = rows.splice(1).map(row => row.replace(/\".*\"/, "").split(",")).filter(fixture => {
                return fixture.length == header.length && fixture[eventIndex] &&
                    parseInt(fixture[eventIndex]) >= gameInformation.CURRENT_GAME_WEEK &&
                    parseInt(fixture[eventIndex]) <= gameInformation.CURRENT_GAME_WEEK + PREDICT_BY_WEEKS - 1
            })

            rows.forEach((fixture, i) => {
                predictBy[newTeams[fixture[hteamIndex]].shortName].games.push(parseInt(fixture[hTeamDifficultyIndex]));
                predictBy[newTeams[fixture[ateamIndex]].shortName].games.push(parseInt(fixture[aTeamDifficultyIndex]));

                if (parseInt(fixture[eventIndex]) == gameInformation.CURRENT_GAME_WEEK) {
                    predictBy[newTeams[fixture[hteamIndex]].shortName].next++;
                    predictBy[newTeams[fixture[ateamIndex]].shortName].next++;
                }
            });

            makeTrainingSet(0);
        })
    })
}

function makeTrainingSet(index) {
    const ts = []
    const playerData = pointsDataSet[Object.keys(pointsDataSet)[index]]
    if (!playerData) {
        fs.writeFile(`./predictedData/${gameInformation.CURRENT_SEASON}/predictedData${gameInformation.CURRENT_GAME_WEEK}.json`, JSON.stringify(masterDataSet).replace(/null,/g, "").replace(/,null/g, ""), function (err) {
            if (err) throw err;
            console.log("Wrote Predicted Data");
            makePredictionFile();
        })
        return;
    }

    console.log(playerData.id, playerData.name)
    if (deletedMembers.includes(playerData.id) || buggedPlayers.includes(playerData.id)) {
        console.log("Deleted");
        return makeTrainingSet(index + 1);
    }

    let sum = 0;
    let numGames = 0;
    let totalGames = 0;
    for (const dataset in playerData) {
        if (!dataset.startsWith("GW")) continue;
        totalGames++;
        ts.push(playerData[dataset].points)
        const roundNum = parseInt(dataset.replace("GW", ""))

        let beginningRound = gameInformation.CURRENT_SEASON_BEGINNING_ROUND;
        if (gameInformation.CURRENT_GAME_WEEK == 1) {
            beginningRound = gameInformation.CURRENT_SEASON_BEGINNING_ROUND - gameInformation.SEASON_LENGTH - gameInformation.CURRENT_GAME_WEEK;
        }

        if (roundNum >= beginningRound) {
            sum += playerData[dataset].points
            numGames++;
        }
    }

    if (!processAllPlayers &&
        (totalGames < gameInformation.MIN_GAMES || sum < gameInformation.MIN_SEASON_PPG * numGames || numGames < (gameInformation.CURRENT_GAME_WEEK == 1 ? gameInformation.SEASON_LENGTH : gameInformation.CURRENT_GAME_WEEK - 1) * gameInformation.MIN_SEASON_GAME_PERC || predictBy[playerData.team].games.length < 1 || totalGames < 2) &&
        !previousTeam.includes(playerData.first_name + " " + playerData.last_name + " " + playerData.name)) {
        console.log("Not min requirements");
        return makeTrainingSet(index + 1);
    }

    if (sum <= 0 || predictBy[playerData.team].games.length == 0) {
        var arima = [0, 0];
        var lstm = [0, 0];
    } else {
        var arima = neuralNetwork.doARIMA(ts, predictBy[playerData.team]);
        var lstm = neuralNetwork.doLSTM(playerData, predictBy[playerData.team]);
    }

    if (arima[0] / lstm[0] > neuralNetwork.MAX_DIFF ||
        lstm[0] / arima[0] > neuralNetwork.MAX_DIFF) {
        arima[0] = arima[1] * PREDICT_BY_WEEKS;
        lstm[0] = lstm[1] * PREDICT_BY_WEEKS;
    }

    if (predictBy[playerData.team].games.length == 0) {
        var p = 0;
        var next = 0;
    } else {
        let ARIMARatio = RATIOS[playerData.team].ARIMA;
        let LSTMRatio = RATIOS[playerData.team].LSTM;
        if (RATIOS[playerData.team][playerData.name]) {
            ARIMARatio = RATIOS[playerData.team][playerData.name].ARIMA;
            LSTMRatio = RATIOS[playerData.team][playerData.name].LSTM;
        }
        var p = (arima[0] * ARIMARatio) + (lstm[0] * LSTMRatio);
        var next = (arima[1] * ARIMARatio) + (lstm[1] * LSTMRatio);
    }

    let found = false;
    for (let i = 0; i < masterDataSet.length; i++) {
        if (!masterDataSet[i]) continue;
        if (masterDataSet[i][masterDataSet[0].indexOf("ID")] == playerData.id) {
            masterDataSet[i].push(arima[0])
            masterDataSet[i].push(lstm[0])
            masterDataSet[i].push(p)
            masterDataSet[i].push(next)
            masterDataSet[i].push(0)
            masterDataSet[i].push(0)
            found = true
        }
    }
    if (!found) {
        console.log(`Couldn't find ${playerData.id}`)
        return;
    }

    makeTrainingSet(index + 1)
}

function makePredictionFile() {
    const workbook = new ExcelJS.Workbook();
    workbook.created = new Date();

    const sheet = workbook.addWorksheet("Sheet1");

    const firstLetterIndex = masterDataSet[0].length + 1;
    let rowIndex = 2;

    sheet.getCell(`${ALPHABET[firstLetterIndex]}${rowIndex}`).value = "Total Points";
    sheet.getCell(`${ALPHABET[firstLetterIndex + 1]}${rowIndex}`).value = {
        formula: "=SUMPRODUCT(Table1[Selected],Table1[PPG])",
        result: -1
    };
    sheet.getCell(`${ALPHABET[firstLetterIndex + 2]}${rowIndex}`).value = "MAX";

    rowIndex += 2;

    sheet.getCell(`${ALPHABET[firstLetterIndex]}${rowIndex}`).value = "Total Cost";
    sheet.getCell(`${ALPHABET[firstLetterIndex + 1]}${rowIndex}`).value = {
        formula: "=SUMPRODUCT(Table1[Selected],Table1[Cost])",
        result: -1
    };
    sheet.getCell(`${ALPHABET[firstLetterIndex + 2]}${rowIndex}`).value = TEAM_WORTH;

    rowIndex += 2;

    sheet.getCell(`${ALPHABET[firstLetterIndex]}${rowIndex}`).value = "GKP";
    sheet.getCell(`${ALPHABET[firstLetterIndex + 1]}${rowIndex}`).value = {
        formula: "=SUMPRODUCT(Table1[Selected],Table1[GKP])",
        result: -1
    };
    sheet.getCell(`${ALPHABET[firstLetterIndex + 2]}${rowIndex}`).value = 2;

    rowIndex++;

    sheet.getCell(`${ALPHABET[firstLetterIndex]}${rowIndex}`).value = "DEF";
    sheet.getCell(`${ALPHABET[firstLetterIndex + 1]}${rowIndex}`).value = {
        formula: "=SUMPRODUCT(Table1[Selected],Table1[DEF])",
        result: -1
    };
    sheet.getCell(`${ALPHABET[firstLetterIndex + 2]}${rowIndex}`).value = 5;

    rowIndex++;

    sheet.getCell(`${ALPHABET[firstLetterIndex]}${rowIndex}`).value = "MID";
    sheet.getCell(`${ALPHABET[firstLetterIndex + 1]}${rowIndex}`).value = {
        formula: "=SUMPRODUCT(Table1[Selected],Table1[MID])",
        result: -1
    };
    sheet.getCell(`${ALPHABET[firstLetterIndex + 2]}${rowIndex}`).value = 5;

    rowIndex++;

    sheet.getCell(`${ALPHABET[firstLetterIndex]}${rowIndex}`).value = "FWD";
    sheet.getCell(`${ALPHABET[firstLetterIndex + 1]}${rowIndex}`).value = {
        formula: "=SUMPRODUCT(Table1[Selected],Table1[FWD])",
        result: -1
    };
    sheet.getCell(`${ALPHABET[firstLetterIndex + 2]}${rowIndex}`).value = 3;

    rowIndex += 2;

    sheet.getCell(`${ALPHABET[firstLetterIndex]}${rowIndex}`).value = "Transfers";
    sheet.getCell(`${ALPHABET[firstLetterIndex + 1]}${rowIndex}`).value = {
        formula: "=SUMPRODUCT(Table1[Selected], -- (Table1[PREV] = 0))",
        result: -1
    };

    rowIndex++;

    sheet.getCell(`${ALPHABET[firstLetterIndex]}${rowIndex}`).value = "Free";
    sheet.getCell(`${ALPHABET[firstLetterIndex + 1]}${rowIndex}`).value = freeTransfers;

    rowIndex += 2;

    sheet.getCell(`${ALPHABET[firstLetterIndex]}${rowIndex}`).value = "Cost";
    sheet.getCell(`${ALPHABET[firstLetterIndex + 1]}${rowIndex}`).value = {
        formula: `=((${ALPHABET[firstLetterIndex + 1]}${rowIndex - 3}-${ALPHABET[firstLetterIndex + 1]}${rowIndex - 2})+ABS((${ALPHABET[firstLetterIndex + 1]}${rowIndex - 3}-${ALPHABET[firstLetterIndex + 1]}${rowIndex - 2})))/2*4`,
        result: -1
    };

    rowIndex += 2;

    sheet.getCell(`${ALPHABET[firstLetterIndex]}${rowIndex}`).value = "Profit";
    sheet.getCell(`${ALPHABET[firstLetterIndex + 1]}${rowIndex}`).value = {
        formula: `=${ALPHABET[firstLetterIndex + 1]}${rowIndex - 14}-${ALPHABET[firstLetterIndex + 1]}${rowIndex - 2}*${PREDICT_BY_WEEKS}`,
        result: -1
    };

    rowIndex += 2;
    for (const teamName of gameInformation.TEAMS) {
        sheet.getCell(`${ALPHABET[firstLetterIndex]}${rowIndex}`).value = teamName;
        sheet.getCell(`${ALPHABET[firstLetterIndex + 1]}${rowIndex}`).value = {
            formula: `=SUMPRODUCT(Table1[Selected],Table1[${teamName}])`,
            result: -1
        };
        sheet.getCell(`${ALPHABET[firstLetterIndex + 2]}${rowIndex}`).value = 3;
        rowIndex++;
    }

    let foundPrev = 0;

    sheet.addTable({
        name: 'Table1',
        ref: "A1",
        headerRow: true,
        style: {
            showRowStripes: true,
        },
        columns: masterDataSet[0].map(header => {
            return {
                name: header,
                filterButton: true
            }
        }),
        rows: masterDataSet.slice(1).filter(player => player[masterDataSet[0].indexOf("Selected")] == 0).map(player => {
            if (previousTeam.includes(player[masterDataSet[0].indexOf("First Name")] + " " + player[masterDataSet[0].indexOf("Surname")] + " " + player[masterDataSet[0].indexOf("Web Name")])) {
                player[masterDataSet[0].indexOf("PREV")] = 1;
                foundPrev++;
            }
            return player;
        })
    });

    for (const colName of HIDDEN_COLUMNS) {
        sheet.getColumn(ALPHABET[masterDataSet[0].indexOf(colName)]).hidden = true;
    }

    if (foundPrev == 15) {
        console.log("Found all previous players!")
    } else {
        console.log(`Found only ${foundPrev} out of 15 previous players`)
    }

    workbook.xlsx.writeFile(`./Predictions/${gameInformation.CURRENT_SEASON}/Week ${gameInformation.CURRENT_GAME_WEEK}.xlsx`);
}

init();