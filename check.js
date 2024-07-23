// check.js
const readline = require('readline');

const rl = readline.createInterface({
    input: process.stdin,
    output: process.stdout,
    terminal: false
});

rl.on('line', (line) => {
    const data = JSON.parse(line);
    const userSpeech = data.userSpeech;

    // 発話終了判定のルール（例: 発話が途切れた時間が一定以上）
    const isFinished = userSpeech.endsWith('。') || userSpeech.endsWith('！') || userSpeech.endsWith('？');

    console.log(JSON.stringify({ isFinished }));
});
