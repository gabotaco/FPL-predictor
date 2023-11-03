const MAX_POINTS = 50;
const RETRY_POINT = 20;
const MAX_RETRIES = 5;
const MAX_DIFF = 3.5;
const neataptic = require("neataptic")
const ARIMA = require("arima");
const arima = new ARIMA({
    auto: true,
    verbose: false
});

let ARIMAcounter = 0;
function doARIMA(ts, predBy) {
    if (ARIMAcounter == MAX_RETRIES) throw "Too many ARIMA calls";
    if (predBy.games.length == 0) return 0;

    let hasNonZero = false;
    let sameNum = ts[0];
    for (const int of ts) {
        if (int > 0) hasNonZero = true;
        if (int != sameNum) sameNum = -Infinity; 
    }
    if (!hasNonZero) return 0;
    if (sameNum > -Infinity) return sameNum;

    arima.train(ts);

    const [pred, errors] = arima.predict(predBy.games.length)
    const next = pred.slice(0, predBy.next).reduce((acc, val) => acc + val, 0);
    const overall = pred.reduce((acc, val) => acc + val, 0);

    if (Number.isNaN(overall) || overall / predBy.games.length >= RETRY_POINT || overall / predBy.games.length <= -RETRY_POINT) {
        console.log('RETRY ARIMA');
        console.log('ts', ts)
        console.log('overall / predBy.games.length', overall / predBy.games.length)
        ARIMAcounter++;
        return doARIMA(ts, predBy);
    }

    ARIMAcounter = 0;
    return [overall, next];
}

let LSTMcounter = 0;
function doLSTM(playerData, predBy) {
    if (LSTMcounter == MAX_RETRIES) throw "Too many LSTM calls" 
    if (predBy.games.length == 0) return 0;

    let trainingSet = [];
    for (let i = 0; i < Object.keys(playerData).length - 1; i++) {
        const gameWeek = Object.keys(playerData)[i]
        if (!gameWeek.startsWith("GW")) continue;
        const adjustedPts = playerData[gameWeek].points / MAX_POINTS;
        if (adjustedPts > 1) throw `${adjustedPts} over 1. Increase MAX_POINTS`

        trainingSet.push({
            input: [adjustedPts, playerData[gameWeek].diff / 5],
            output: [playerData[Object.keys(playerData)[i + 1]].points / MAX_POINTS]
        });
    }

    if (trainingSet.length == 0) return 0;

    let hasNonZero = false;
    for (let i = 0; i < trainingSet.length; i++) {
        if (trainingSet[i].input[0] != 0 || trainingSet[i].output[0] != 0) {
            hasNonZero = true;
            break;
        }
    }

    if (!hasNonZero) return 0;

    const LSTMNetwork = neataptic.architect.LSTM(2, 3, 1);
    LSTMNetwork.train(trainingSet, {
        error: 0.5 / MAX_POINTS,
        clear: true,
        log: 1000
    });

    
    var input = playerData[Object.keys(playerData)[Object.keys(playerData).length - 1]].points / MAX_POINTS;
    var output = LSTMNetwork.activate([input, predBy.games[0] / 5])
    let pred = [output * MAX_POINTS]
    let overall = pred[0]

    for (var i = 1; i < predBy.games.length; i++) {
        input = output;
        var output = LSTMNetwork.activate([input, predBy.games[i] / 5])
        pred.push(output * MAX_POINTS)
        overall += output * MAX_POINTS
    }

    if (Number.isNaN(overall) || overall / predBy.games.length >= RETRY_POINT || overall / predBy.games.length <= -RETRY_POINT) {
        console.log('RETRY LSTM');
        console.log('trainingSet', trainingSet);
        console.log('overall / predBy.games.length', overall / predBy.games.length)
        LSTMcounter++;
        return doLSTM(playerData, predBy);
    }

    LSTMcounter = 0;
    return [overall, pred.slice(0, predBy.next).reduce((acc, val) => acc + val, 0)];
}

module.exports = { doARIMA, doLSTM, RETRY_POINT, MAX_DIFF }