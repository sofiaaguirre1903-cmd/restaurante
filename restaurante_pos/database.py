import sqlite3
import os

def init_db():
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    db_path = os.path.join(BASE_DIR, 'restaurante.db')

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS productos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL,
            precio REAL NOT NULL
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS mesas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL,
            estado TEXT DEFAULT 'Libre'
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS ventas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            mesa_id INTEGER NOT NULL,
            fecha_apertura TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            fecha_cierre TIMESTAMP,
            total REAL DEFAULT 0,
            estado TEXT DEFAULT 'Abierta',
            FOREIGN KEY (mesa_id) REFERENCES mesas (id)
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS detalle_venta (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            venta_id INTEGER NOT NULL,
            producto_id INTEGER NOT NULL,
            producto_nombre TEXT NOT NULL,
            precio REAL NOT NULL,
            cantidad INTEGER DEFAULT 1,
            FOREIGN KEY (venta_id) REFERENCES ventas (id)
        )
    ''')

    # Crear 8 mesas vacías
    cursor.execute('SELECT COUNT(*) FROM mesas')
    if cursor.fetchone()[0] == 0:
        for i in range(1, 9):
            cursor.execute('INSERT INTO mesas (nombre) VALUES (?)', (f'Mesa {i}',))

    conn.commit()
    conn.close()

if __name__ == '__main__':
    init_db()
    print("¡Base de datos limpia creada correctamente!")