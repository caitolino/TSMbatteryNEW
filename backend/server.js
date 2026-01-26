const express = require('express');
const mongoose = require('mongoose')();
const cors = require("cors");


const app = express();
app.use(cors());
app.use(express.json());

const MONGO_URI = "mongodb://TSM-5CD2182GXS:27017/batterijbeheer"

mongoose.connect(MONGO_URI, {useNewUrlParser: true, useUnifiedTopology: true})
    .then(() => console.log("connect"));
    .catch(err => console.error("connection error:", err));

const batterijenSchema = new mongoose.Schema({}, {collection: "batterijen"})
const Batterijen = mongoose.model("Test", testSchema);

app.get("/api/batterijen", async (req, res) => {
    try {
        const data = await Batterijen.find();
        res.json(data);
    } catch (err) {res.status(500).json({error: err.lessage});
}
});
app.post("/api/batterijen", async (req, res) => {
    try {
        const newItem = new Test(req.body);
        await newItem.save();
        res.json(newItem);
    } catch (err) {
        res.status(500).json({error: err.message });
    }
});


app.listen(3000, () => {
    console.log('Server is running on http://TSM-5CD2182GXS:3000')
})

