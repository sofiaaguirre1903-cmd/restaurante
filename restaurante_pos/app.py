from flask import Flask, render_template, request, redirect, url_for
import sqlite3
import os

app = Flask(__name__)

def get_db():
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    db_path = os.path.join(BASE_DIR, 'restaurante.db')
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn

@app.route('/')
def inicio():
    return render_template('index.html')

@app.route('/mesas')
def ver_mesas():
    conn = get_db()
    mesas = conn.execute('SELECT * FROM mesas ORDER BY id ASC').fetchall()
    
    ventas_abiertas = conn.execute('''
        SELECT v.*, m.nombre as mesa_nombre 
        FROM ventas v JOIN mesas m ON v.mesa_id = m.id 
        WHERE v.estado = 'Abierta'
    ''').fetchall()

    ventas_cerradas = conn.execute('''
        SELECT v.*, m.nombre as mesa_nombre 
        FROM ventas v JOIN mesas m ON v.mesa_id = m.id 
        WHERE v.estado = 'Cerrada' 
        ORDER BY v.fecha_cierre DESC
    ''').fetchall()
    
    conn.close()
    return render_template('mesas.html', mesas=mesas, abiertas=ventas_abiertas, cerradas=ventas_cerradas)

# Ruta para crear una nueva mesa dinámicamente
@app.route('/mesa/crear', methods=['POST'])
def crear_mesa():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT COUNT(*) FROM mesas')
    total_mesas = cursor.fetchone()[0]
    
    nombre_nueva_mesa = f'Mesa {total_mesas + 1}'
    conn.execute('INSERT INTO mesas (nombre) VALUES (?)', (nombre_nueva_mesa,))
    conn.commit()
    conn.close()
    return redirect(url_for('ver_mesas'))

# Ruta para eliminar una mesa
@app.route('/mesa/eliminar/<int:mesa_id>')
def eliminar_mesa(mesa_id):
    conn = get_db()
    # Solo elimina si no tiene una venta abierta
    venta_abierta = conn.execute('SELECT * FROM ventas WHERE mesa_id = ? AND estado = "Abierta"', (mesa_id,)).fetchone()
    if not venta_abierta:
        conn.execute('DELETE FROM mesas WHERE id = ?', (mesa_id,))
        conn.commit()
    conn.close()
    return redirect(url_for('ver_mesas'))

@app.route('/mesa/<int:mesa_id>')
def detalle_mesa(mesa_id):
    conn = get_db()
    mesa = conn.execute('SELECT * FROM mesas WHERE id = ?', (mesa_id,)).fetchone()
    
    venta = conn.execute('SELECT * FROM ventas WHERE mesa_id = ? AND estado = "Abierta"', (mesa_id,)).fetchone()
    if not venta:
        cursor = conn.cursor()
        cursor.execute('INSERT INTO ventas (mesa_id) VALUES (?)', (mesa_id,))
        conn.commit()
        venta_id = cursor.lastrowid
        conn.execute('UPDATE mesas SET estado = "Ocupada" WHERE id = ?', (mesa_id,))
        conn.commit()
        venta = conn.execute('SELECT * FROM ventas WHERE id = ?', (venta_id,)).fetchone()

    detalles = conn.execute('SELECT * FROM detalle_venta WHERE venta_id = ?', (venta['id'],)).fetchall()
    productos = conn.execute('SELECT * FROM productos ORDER BY nombre ASC').fetchall()
    
    total = sum(d['precio'] * d['cantidad'] for d in detalles)
    conn.execute('UPDATE ventas SET total = ? WHERE id = ?', (total, venta['id']))
    conn.commit()

    conn.close()
    return render_template('detalle_mesa.html', mesa=mesa, venta=venta, detalles=detalles, productos=productos, total=total)

@app.route('/mesa/renombrar/<int:mesa_id>', methods=['POST'])
def renombrar_mesa(mesa_id):
    nuevo_nombre = request.form.get('nombre')
    if nuevo_nombre:
        conn = get_db()
        conn.execute('UPDATE mesas SET nombre = ? WHERE id = ?', (nuevo_nombre, mesa_id))
        conn.commit()
        conn.close()
    return redirect(url_for('detalle_mesa', mesa_id=mesa_id))

@app.route('/venta/agregar', methods=['POST'])
def agregar_producto_venta():
    venta_id = request.form.get('venta_id')
    mesa_id = request.form.get('mesa_id')
    producto_id = request.form.get('producto_id')

    if producto_id:
        conn = get_db()
        prod = conn.execute('SELECT * FROM productos WHERE id = ?', (producto_id,)).fetchone()
        
        existente = conn.execute('SELECT * FROM detalle_venta WHERE venta_id = ? AND producto_id = ?', 
                                 (venta_id, producto_id)).fetchone()
        if existente:
            conn.execute('UPDATE detalle_venta SET cantidad = cantidad + 1 WHERE id = ?', (existente['id'],))
        else:
            conn.execute('''
                INSERT INTO detalle_venta (venta_id, producto_id, producto_nombre, precio, cantidad) 
                VALUES (?, ?, ?, ?, 1)
            ''', (venta_id, prod['id'], prod['nombre'], prod['precio']))

        conn.commit()
        conn.close()
    return redirect(url_for('detalle_mesa', mesa_id=mesa_id))

@app.route('/detalle/cantidad/<int:detalle_id>/<string:accion>')
def cambiar_cantidad(detalle_id, accion):
    conn = get_db()
    item = conn.execute('SELECT * FROM detalle_venta WHERE id = ?', (detalle_id,)).fetchone()
    venta = conn.execute('SELECT * FROM ventas WHERE id = ?', (item['venta_id'],)).fetchone()
    
    if accion == 'sumar':
        conn.execute('UPDATE detalle_venta SET cantidad = cantidad + 1 WHERE id = ?', (detalle_id,))
    elif accion == 'restar':
        if item['cantidad'] > 1:
            conn.execute('UPDATE detalle_venta SET cantidad = cantidad - 1 WHERE id = ?', (detalle_id,))
        else:
            conn.execute('DELETE FROM detalle_venta WHERE id = ?', (detalle_id,))

    conn.commit()
    conn.close()
    return redirect(url_for('detalle_mesa', mesa_id=venta['mesa_id']))

@app.route('/detalle/eliminar/<int:detalle_id>')
def eliminar_detalle(detalle_id):
    conn = get_db()
    item = conn.execute('SELECT * FROM detalle_venta WHERE id = ?', (detalle_id,)).fetchone()
    venta = conn.execute('SELECT * FROM ventas WHERE id = ?', (item['venta_id'],)).fetchone()
    
    conn.execute('DELETE FROM detalle_venta WHERE id = ?', (detalle_id,))
    conn.commit()
    conn.close()
    return redirect(url_for('detalle_mesa', mesa_id=venta['mesa_id']))

@app.route('/mesa/cerrar/<int:venta_id>', methods=['POST'])
def cerrar_mesa(venta_id):
    conn = get_db()
    venta = conn.execute('SELECT * FROM ventas WHERE id = ?', (venta_id,)).fetchone()
    
    conn.execute('UPDATE ventas SET estado = "Cerrada", fecha_cierre = CURRENT_TIMESTAMP WHERE id = ?', (venta_id,))
    conn.execute('UPDATE mesas SET estado = "Libre" WHERE id = ?', (venta['mesa_id'],))
    conn.commit()
    conn.close()
    return redirect(url_for('ver_mesas'))

# Ruta para ELIMINAR una cuenta/venta del historial
@app.route('/venta/eliminar/<int:venta_id>')
def eliminar_venta(venta_id):
    conn = get_db()
    conn.execute('DELETE FROM detalle_venta WHERE venta_id = ?', (venta_id,))
    conn.execute('DELETE FROM ventas WHERE id = ?', (venta_id,))
    conn.commit()
    conn.close()
    return redirect(request.referrer or url_for('ver_mesas'))

@app.route('/productos', methods=['GET', 'POST'])
def productos():
    conn = get_db()
    if request.method == 'POST':
        nombre = request.form.get('nombre')
        precio = request.form.get('precio')
        if nombre and precio:
            conn.execute('INSERT INTO productos (nombre, precio) VALUES (?, ?)', (nombre, float(precio)))
            conn.commit()
            return redirect(url_for('productos'))

    lista_productos = conn.execute('SELECT * FROM productos ORDER BY id DESC').fetchall()
    conn.close()
    return render_template('productos.html', productos=lista_productos)

@app.route('/productos/eliminar/<int:producto_id>')
def eliminar_producto(producto_id):
    conn = get_db()
    conn.execute('DELETE FROM productos WHERE id = ?', (producto_id,))
    conn.commit()
    conn.close()
    return redirect(url_for('productos'))

@app.route('/cierre')
def cierre_dia():
    conn = get_db()
    resultado = conn.execute('SELECT SUM(total) as total_dia, COUNT(*) as cantidad_cuentas FROM ventas WHERE estado = "Cerrada"').fetchone()
    cuentas_cerradas = conn.execute('''
        SELECT v.*, m.nombre as mesa_nombre 
        FROM ventas v JOIN mesas m ON v.mesa_id = m.id 
        WHERE v.estado = "Cerrada" 
        ORDER BY v.fecha_cierre DESC
    ''').fetchall()
    
    conn.close()
    total_dia = resultado['total_dia'] if resultado['total_dia'] else 0.0
    cantidad = resultado['cantidad_cuentas'] if resultado['cantidad_cuentas'] else 0
    return render_template('cierre.html', total_dia=total_dia, cantidad=cantidad, cuentas=cuentas_cerradas)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)