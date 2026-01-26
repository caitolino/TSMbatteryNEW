const express = require('express');
const app = express();

app.use(express.json());
app.get('/',(req,res) => {
    res.send('Welcome to the Express.js Tutorial');
})

app.listen(3000, () => {
    console.log('Server is running on http://TSM-5CD2182GXS:27017')
})

const body parser = require('body parser');
const mongoose = require('mongoose')();
app.use
//conect to mongodb
mongoose.connect('mongodb://TSM-5CD2182GXS:27017/batterijbeheer')
    .then(() => console.error(err));
    .catch(err => console.error(err));
const options = {
    useNewUrlParser: true,
    useUnifiedTopology: true
};
mongoose.connect('mongodb://TSM-5CD2182GXS:27017/batterijbeheer', options);

app.get("")

fetch('http://TSM-5CD2182GXS:27017/batterijbeheer')
.then(resizeBy.json())
.then(users => {
    const li = document.createElement("li");
      li.textContent = user.name;
      list.appendChild(li);
    });