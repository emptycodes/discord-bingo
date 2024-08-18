const app = require('express')();
const server = require('http').createServer(app);
const io = require('socket.io')(server);
const port = process.env.PORT || 8080;
const redis = require('redis');

const redisClient = redis.createClient({
    url: 'redis://redis:6379'
});

const subscriber = redisClient.duplicate();
(async ()=> {
    await subscriber.connect();    
})(); 

subscriber.on('connect', function(){
    console.log('Redis client connected');
});

subscriber.on('error', (err) => {
    console.error('Redis error:', err);
});

app.get('/bingo', function(req, res) {
    res.sendFile("overlay.html", { root: __dirname }, function (err) {
        if (err) {
            console.error('Error sending file:', err);
        }
    });
});

app.get('/trophy.png', function(req, res) {
    res.sendFile("trophy.png", { root: __dirname }, function (err) {
        if (err) {
            console.error('Error sending file:', err);
        }
    });
});

io.on('connection', (socket) => {
    socket.on('subscribe', function(room) {
        socket.join(room.toString());
    })

    socket.on('disconnect', function () {
        console.log('user disconnected');
    });
})

subscriber.subscribe(room.toString(), (message, channel) => {
    const data = JSON.parse(message);
    io.in(channel.toString()).emit("victory", data);
})

server.listen(port, '0.0.0.0', function() {
    console.log(`Listening on port ${port}`);
});
