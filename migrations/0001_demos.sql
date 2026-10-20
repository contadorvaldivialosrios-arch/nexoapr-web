-- Solicitudes de demostración enviadas desde el formulario de nexoapr.cl
CREATE TABLE IF NOT EXISTS demos (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  creado TEXT NOT NULL DEFAULT (datetime('now')),
  nombre TEXT NOT NULL,
  cargo TEXT,
  telefono TEXT NOT NULL,
  correo TEXT,
  comite TEXT NOT NULL,
  comuna TEXT,
  socios INTEGER,
  sistema_actual TEXT,
  mensaje TEXT,
  origen TEXT,
  ip_hash TEXT,
  correo_enviado INTEGER NOT NULL DEFAULT 0,
  estado TEXT NOT NULL DEFAULT 'nueva'
);
CREATE INDEX IF NOT EXISTS idx_demos_creado ON demos(creado);
CREATE INDEX IF NOT EXISTS idx_demos_ip ON demos(ip_hash, creado);
