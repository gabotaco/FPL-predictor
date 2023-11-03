const TEAM = {"id": "5950818", "name": "Gabowabo"}

const account = require("./auth.json");
const request = require("request").defaults({
    jar: true,
});

function logIn() {
    return new Promise((resolve, reject) => {
        request.post({
            url: `https://users.premierleague.com/accounts/login/`,
            formData: {
                "password": account.password,
                "login": account.username,
                "redirect_uri": "https://fantasy.premierleague.com/",
                "app": "plfpl-web"
            }
        }, function (err, response) {
            if (err) throw err;
            resolve();
        });
    });
}

module.exports = {request, logIn, TEAM};