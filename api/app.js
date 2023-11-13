const express  = require('express' );
const mongoose = require('mongoose');
const simpleGit= require('simple-git')

const port = 80; 

const MONGO_USERNAME = process.env.MONGO_INITDB_ROOT_USERNAME
const MONGO_PASSWORD = process.env.MONGO_INITDB_ROOT_PASSWORD
const MONGO_DB_NAME  = process.env.MONGO_INITDB_DATABASE
const MONGO_HOST     = 'localhost'
const MONGO_URI      = `mongodb://${MONGO_USERNAME}:${MONGO_PASSWORD}@${MONGO_HOST}:27017/${MONGO_DB_NAME}?authSource=admin`;


const Device = mongoose.model('Device', {
  device_name : String,
  device_count: Number,
})

const getCommitHash = () => {
  return new Promise((resolve, reject) => {
    const git = simpleGit();
    git.revparse(['HEAD'], (err, result) => {
      if (err) {
        reject(err);
      } else {
        resolve(result.trim());
      }
    });
  });
}

mongoose
  .connect(MONGO_URI, {useNewUrlParser: true})
  .then(() => { 
    const app = express();
    app.use(express.json())

    app.get('/', (req, res) => {
       try {
          const commitHash = getCommitHash()
          res.json({commitHash: commitHash})
       } catch(error) {
          console.error(error);
          res.status(500).json({ error: 'Internal Server Error' });
       }
    });

    app.get('/devices', async (req, res) => {
      try {
        const devices = await Device.find()
        res.json(devices)
      } catch(error) {
        res.status(500).send(error)
      }
    });

    app.get('/devices/:id', async (req, res) => {
      try {
        const device = await Device.findById(req.params.id)
        if(!device) {
          return res.status(404).send("Item was not found")
        }
        res.json(device)
      } catch(error) {
        res.status(500).send(error)
      }
    });

    app.post('/devices', async (req, res) => {
      try {
        const device = new Device(req.body)
        await device.save()
        res.json(device)
      } catch(error) {
        res.status(500).send(error)
      }
    });

    app.put('/devices/:id', async (req, res) => {
      try {
        const device = await Device.FindByIdAndUpdate(req.params.id, req.body, {new: true})
        if(!device) {
          return res.status(404).send("Device not found")
        }
        res.json(device)
    } catch(error) {
        res.status(500).send(error)
    }
    })

    app.delete('/devices/:id', async (req, res) => {
      try {
        const device = Device.findByIdAndDelete(req.params.id)
        if(!device) {
          return res.status(404).send("Device not found")
        }
        res.json({ message: "Item deleted succesfully" })
      } catch(error) {
        res.status(500).send(error)
      }
    })

    app.listen(port, () => {
      console.log(`Server is running on port ${port}`);
    });
})
