const express = require('express');
const multer = require('multer');
const path = require('path');
const fs = require('fs');

const app = express();
const PORT = process.env.PORT || 3000;

// Directory where game saves are stored
const storageDir = path.join(__dirname, 'saves');
if (!fs.existsSync(storageDir)) {
  fs.mkdirSync(storageDir, { recursive: true });
}

// Storage configuration (overwrites slimerancher2.zip on each upload)
const storage = multer.diskStorage({
  destination: (req, file, cb) => cb(null, storageDir),
  filename: (req, file, cb) => cb(null, `${req.params.gameId}.zip`)
});

const upload = multer({ storage });

// Endpoint to receive save upload from client
app.post('/api/upload/:gameId', upload.single('savefile'), (req, res) => {
  console.log(`[+] Received save update for: ${req.params.gameId}`);
  res.json({ status: 'success', message: 'Save file stored successfully' });
});

// Endpoint to send save file to client
app.get('/api/download/:gameId', (req, res) => {
  const filePath = path.join(storageDir, `${req.params.gameId}.zip`);
  if (fs.existsSync(filePath)) {
    res.download(filePath);
  } else {
    res.status(404).json({ error: 'Save file not found on server' });
  }
});

app.listen(PORT, () => {
  console.log(`[+] Game Save Sync Server listening on port ${PORT}`);
});