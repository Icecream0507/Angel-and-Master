const express = require('express');
const http = require('http');
const { Server } = require('socket.io');
const path = require('path');

const app = express();
const server = http.createServer(app);
const io = new Server(server);

// 静态文件服务
app.use(express.static(path.join(__dirname, 'public')));

let players = [];
let isGameStarted = false;

// 玩家配对函数
function assignRoles() {
    if (players.length < 2) {
        return; // 至少需要两名玩家
    }
    const shuffledPlayers = [...players].sort(() => 0.5 - Math.random());
    
    // 简单地将打乱后的列表与原列表进行配对
    for (let i = 0; i < players.length; i++) {
        const angel = players[i];
        const master = shuffledPlayers[i];

        // 避免自己是自己的主人
        if (angel.id === master.id) {
            // 如果自己是自己的主人，就和下一个玩家交换
            const nextIndex = (i + 1) % players.length;
            const temp = shuffledPlayers[i];
            shuffledPlayers[i] = shuffledPlayers[nextIndex];
            shuffledPlayers[nextIndex] = temp;
            
            master = shuffledPlayers[i];
        }

        angel.masterId = master.id;
        angel.masterName = master.nickname;
    }
}

io.on('connection', (socket) => {
    console.log(`一个新玩家加入了: ${socket.id}`);

    if (isGameStarted) {
        socket.emit('game_status', '游戏已经开始了，请等待下一轮。');
        return;
    }

    socket.on('join', (nickname) => {
        if (players.find(p => p.nickname === nickname)) {
            socket.emit('game_status', '该昵称已被占用，请换一个。');
            return;
        }

        const newPlayer = {
            id: socket.id,
            nickname: nickname,
            masterId: null,
            masterName: null,
            wishes: []
        };
        players.push(newPlayer);
        console.log(`玩家 ${nickname} 加入了游戏。当前玩家数: ${players.length}`);

        io.emit('game_status', `玩家 ${nickname} 加入了。当前玩家数: ${players.length}。`);

        // 假设有2个或更多玩家就自动开始游戏
        if (players.length >= 2) {
            isGameStarted = true;
            assignRoles();
            players.forEach(player => {
                io.to(player.id).emit('start_game', {
                    isGameStarted: true,
                    masterName: player.masterName
                });
            });
            console.log("游戏已开始，角色已分配。");
        }
    });

    socket.on('add_wish', (data) => {
        const player = players.find(p => p.id === socket.id);
        if (player && player.wishes.length < 3) {
            player.wishes.push(data.wish);
            // 这里可以添加逻辑，将愿望发送给对应的主人
            // 简单的 demo 中，我们只是收集愿望
            console.log(`玩家 ${player.nickname} 许下了愿望: ${data.wish}`);
        }
    });

    socket.on('disconnect', () => {
        const playerIndex = players.findIndex(p => p.id === socket.id);
        if (playerIndex !== -1) {
            const disconnectedPlayer = players.splice(playerIndex, 1)[0];
            console.log(`玩家 ${disconnectedPlayer.nickname} 离开了。`);
            io.emit('game_status', `玩家 ${disconnectedPlayer.nickname} 离开了。当前玩家数: ${players.length}`);

            if (players.length < 2) {
                isGameStarted = false;
                players = [];
                io.emit('game_status', '玩家不足，游戏已重置，等待新玩家加入...');
            }
        }
    });
});

const PORT = process.env.PORT || 3000;
server.listen(PORT, () => {
    console.log(`服务器正在运行: http://localhost:${PORT}`);
    console.log('打开浏览器，访问该地址，然后让你的朋友们也加入吧！');
});