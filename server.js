import express from "express";
import fs from "fs";
import path from "path";

const app = express();
const PORT = process.env.PORT || 3000;
const PERSISTENT_DIR = process.env.PERSISTENT_DIR || ".";
const historyFile = path.join(PERSISTENT_DIR, "history.json");

app.use(express.json());
app.use(express.static("."));

// Crear archivo si no existe
if (!fs.existsSync(historyFile)) {
  fs.writeFileSync(historyFile, JSON.stringify([]));
}

// Guardar cambios
app.post("/save", (req, res) => {
  const { carrito, estatus, comentario } = req.body;
  if (!carrito || !estatus) return res.status(400).send("Faltan datos");

  const historial = JSON.parse(fs.readFileSync(historyFile, "utf-8"));
  const entry = {
    carrito,
    estatus,
    comentario: comentario || "",
    fecha: new Date().toISOString().split("T")[0],
    hora: new Date().toLocaleTimeString()
  };
  historial.push(entry);
  fs.writeFileSync(historyFile, JSON.stringify(historial, null, 2));
  res.json({ ok: true });
});

// Consultar historial
app.get("/history", (req, res) => {
  const { carrito, fecha } = req.query;
  const historial = JSON.parse(fs.readFileSync(historyFile, "utf-8"));

  const filtered = historial.filter(h => h.carrito === carrito && h.fecha === fecha);
  res.json(filtered);
});

app.listen(PORT, () => console.log(`Servidor corriendo en http://localhost:${PORT}`));
