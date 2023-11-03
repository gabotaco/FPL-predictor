const CALIBRATE_BY = 10;
const buggedPlayers = [];
const headers = ["Name", "ARIMAPP", "LSTMPP", "PP", "AP", "DIFF"];

const ExcelJS = require("exceljs");
const gameInformation = require("./game_information")
const neuralNetwork = require("./neuralNetwork")
const datasetMaker = require("./makeDataset")

const processAllPlayers = false;

const players = {}
let pointsDataSet;

function init() {
    for (const team of gameInformation.TEAMS) {
        players[team] = [];
    }


    datasetMaker.getDataset().then(datasets => {
        pointsDataSet = datasets.points;
        getBasicPlayersTeams();
    })
}

function getBasicPlayersTeams() {
    for (const playerId in pointsDataSet) {
        const playerData = pointsDataSet[playerId];

        players[playerData.team].push(playerData);
    }

    getPlayerPredictions();
}

function getPlayerPredictions() {
    for (const team of gameInformation.TEAMS) {
        players[team].forEach((playerData, index) => {
            console.log(playerData.id, playerData.name);
            if (buggedPlayers.includes(playerData.id)) return;

            let sum = 0;
            let numGames = 0;
            let totalGames = 0;
            const gws = [];
            for (const dataset in playerData) {
                if (!dataset.startsWith("GW")) continue;
                totalGames++;
                gws.push(playerData[dataset])
                const roundNum = parseInt(dataset.replace("GW", ""))
                
                let beginningRound = gameInformation.CURRENT_SEASON_BEGINNING_ROUND;
                if (gameInformation.CURRENT_GAME_WEEK == 1) {
                    beginningRound = gameInformation.CURRENT_SEASON_BEGINNING_ROUND - gameInformation.SEASON_LENGTH - 1;
                }
        
                if (roundNum >= beginningRound) {
                    sum += playerData[dataset].points
                    numGames++;
                }
            }

            if (!processAllPlayers && 
                (totalGames - CALIBRATE_BY < gameInformation.MIN_GAMES || sum < gameInformation.MIN_SEASON_PPG * numGames || numGames < (gameInformation.CURRENT_GAME_WEEK == 1 ? gameInformation.SEASON_LENGTH : gameInformation.CURRENT_GAME_WEEK - 1) * gameInformation.MIN_SEASON_GAME_PERC || totalGames < 2)) {
                console.log("Not min requirements");
                return;
            }        

            const predBy = {"games": [], "next": 0};
            const trainingPlayerData = {};
            let i;
            for (i = 0; i < gws.length - CALIBRATE_BY; i++) {
                trainingPlayerData[`GW${i + 1}`] = gws[i];
            }
            for (; i < gws.length; i++) {
                predBy.games.push(gws[i].diff)
            }

            if (sum <= 0 || gws.length <= CALIBRATE_BY) {
                var arima = 0;
                var lstm = 0;
            } else {
                var arima = neuralNetwork.doARIMA(gws.slice(0, -CALIBRATE_BY).map((val) => val.points), predBy)[0];

                var lstm = neuralNetwork.doLSTM(trainingPlayerData, predBy)[0];

                if (arima / lstm > neuralNetwork.MAX_DIFF || lstm / arima > neuralNetwork.MAX_DIFF) {
                    arima = 0;
                    lstm = 0;
                }
            }
            
            players[team][index] = {
                name: playerData.name,
                gws,
                arima: arima,
                lstm: lstm
            }
        })
    }

    createCalibrationFile();
}

function createCalibrationFile() {
    const workbook = new ExcelJS.Workbook();
    workbook.created = new Date();

    for (const team of gameInformation.TEAMS) {
        if (players[team].filter(player => player.arima != 0 && player.lstm != 0 && player.arima >= -neuralNetwork.RETRY_POINT * CALIBRATE_BY && player.lstm >= -neuralNetwork.RETRY_POINT * CALIBRATE_BY && player.arima <= neuralNetwork.RETRY_POINT * CALIBRATE_BY && player.lstm <= neuralNetwork.RETRY_POINT * CALIBRATE_BY && player.gws.slice(-CALIBRATE_BY).map((obj) => obj.points).reduce((acc, val) => acc + val, 0) >= CALIBRATE_BY * gameInformation.MIN_SEASON_PPG).length == 0) {
            console.log(`Could not find any players for ${team}`);
            continue;
        }
        const sheet = workbook.addWorksheet(team);

        sheet.getCell("H2").value = "ARIMA";
        sheet.getCell("I2").value = 0;

        sheet.getCell("H3").value = "LSTM";
        sheet.getCell("I3").value = 0;

        sheet.getCell("H5").value = "OFF";
        sheet.getCell("I5").value = {formula: `=(SUM(Table${team}[PP]-Table${team}[AP]))^2`, result: -1};
        
        sheet.getCell("H7").value = "AVG";
        sheet.getCell("I7").value = {formula: `=AVERAGE(Table${team}[DIFF])/${CALIBRATE_BY}`, result: -1};

        sheet.addTable({
            name: `Table${team}`,
            ref: "A1",
            headerRow: true,
            style: {
                showRowStripes: true
            },
            columns: headers.map(header => {
                return {
                    name: header,
                    key: header,
                    filterButton: true
                }
            }),
            rows: players[team].filter(player => player.arima != 0 && player.lstm != 0 && player.arima >= -neuralNetwork.RETRY_POINT * CALIBRATE_BY && player.lstm >= -neuralNetwork.RETRY_POINT * CALIBRATE_BY && player.arima <= neuralNetwork.RETRY_POINT * CALIBRATE_BY && player.lstm <= neuralNetwork.RETRY_POINT * CALIBRATE_BY && player.gws.slice(-CALIBRATE_BY).map((obj) => obj.points).reduce((acc, val) => acc + val, 0) >= CALIBRATE_BY * gameInformation.MIN_SEASON_PPG).map(player => {
                return [player.name,
                        player.arima, 
                        player.lstm, 
                        {formula: `=[@ARIMAPP]*$I$2+[@LSTMPP]*$I$3`, result: -1}, 
                        player.gws.slice(-CALIBRATE_BY).map((obj) => obj.points).reduce((acc, val) => acc + val, 0),
                        {formula: `=ABS([@PP]-[@AP])`, result: -1}
                    ];
            })
        });

        sheet.addConditionalFormatting({
            ref: 'I7',
            rules: [
                {
                    type: 'colorScale',
                    cfvo: [
                        {
                            type: 'num',
                            value: 0
                        },
                        {
                            type: 'num',
                            value: 1
                        },
                        {
                            type: 'num',
                            value: 2
                        }
                    ],
                    color: [
                        {
                            argb: '00FF00'
                        },
                        {
                            argb: 'FFFF00'
                        },
                        {
                            argb: 'FF0000'
                        }
                    ]
                }
            ]
        })
    }

    workbook.xlsx.writeFile(`./Calibrations/${gameInformation.CURRENT_SEASON}/Week ${gameInformation.CURRENT_GAME_WEEK}.xlsx`);
}


init();