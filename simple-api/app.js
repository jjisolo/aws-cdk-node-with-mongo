const express  = require('express' );
const mongoose = require('mongoose');

const port = 80; 

const MONGO_URI="mongodb+srv://jjisolo:testtest@cluster0.5erxpbu.mongodb.net/?retryWrites=true&w=majority";

const Device = mongoose.model('Device', {
  device_name : String,
  device_count: Number,
})

mongoose
  .connect(MONGO_URI, { useNewUrlParser: true })
  .then(() => {
    const app = express();
    app.use(express.json())

    app.get('/', (req, res) => {
      res.send('Hello, AWS!');
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
