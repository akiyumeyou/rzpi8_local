const axios = require('axios');

const OPENAI_API_KEY = '';

const prompt = process.argv[2];
const pastMessages = JSON.parse(process.argv[3] || "[]");

const aiMessage = {
    role: "user",
    content: prompt
};

const systemMessage = {
    role: "system",
    content: "あなたは高齢者に寄り添う会話の専門家です。楽しく長時間会話ができるように寄り添います。ユーザーが話すことに対して、相手の話を促進するようにしてください。話の内容に興味を持ち、適度に質問を加えて会話を広げます。話が途切れた場合には、しばらく待って呼びかけをしてください。楽しく、笑顔になれる会話をします。必ず短く的確に応えてください。"
};

if (pastMessages.length === 0) {
    pastMessages.unshift(systemMessage);
}

pastMessages.push(aiMessage);

async function getOpenAIResponse() {
    try {
        const response = await axios.post('https://api.openai.com/v1/chat/completions', {
            model: 'gpt-4-turbo',
            messages: pastMessages,
            max_tokens: 100,
            stop: ["。", "！", "？"],
        }, {
            headers: {
                'Authorization': `Bearer ${OPENAI_API_KEY}`,
                'Content-Type': 'application/json',
            }
        });
        const responseMessage = response.data.choices[0].message.content;
        pastMessages.push({ role: "assistant", content: responseMessage });
        console.log(JSON.stringify({ responseMessage: responseMessage, pastMessages }));
    } catch (error) {
        console.error('API request failed: ', error.message);
        if (error.response) {
            console.error('Error response: ', error.response.data);
        } else {
            console.error('No response data');
        }
        process.exit(1);
    }
}

getOpenAIResponse();
