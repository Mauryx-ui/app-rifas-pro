from flask import Flask, render_template, request, redirect, url_for, session
import sqlite3
from datetime import datetime
import urllib.parse

app = Flask(__name__)
app.secret_key = "clave_maury_rifas_segura_2026"

def init_db():
    conn = sqlite3.connect("db.sqlite3")
    c = conn.cursor()
    
    # Detección y corrección automática de esquema de base de datos
    c.execute("PRAGMA table_info(configuracion)")
    columnas = [col[1] for col in c.fetchall()]
    
    # Si la base de datos es antigua y no tiene 'canal_contacto', la reiniciamos limpiamente
    if columnas and "canal_contacto" not in columnas:
        c.execute("DROP TABLE IF EXISTS configuracion")
        c.execute("DROP TABLE IF EXISTS apartados")
    
    # 1. Configuración de Rifa
    c.execute('''CREATE TABLE IF NOT EXISTS configuracion (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    titulo TEXT,
                    organizador TEXT,
                    canal_contacto TEXT,
                    contacto_detalles TEXT,
                    lugar_residencia TEXT,
                    lugar_juego TEXT,
                    modalidad TEXT,
                    cifras INTEGER,
                    premio TEXT,
                    moneda TEXT,
                    tipo_precio TEXT,
                    precio_base REAL,
                    metodos_pago TEXT,
                    detalles_pago TEXT,
                    loteria TEXT,
                    imagen_url TEXT,
                    fecha_sorteo TEXT
                )''')
                
    # 2. Apartados / Ventas
    c.execute('''CREATE TABLE IF NOT EXISTS apartados (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    rifa_id INTEGER,
                    nombre TEXT,
                    contacto TEXT,
                    residencia TEXT,
                    numero TEXT,
                    valor_pagado REAL,
                    vendedor TEXT,
                    estado TEXT,
                    fecha TEXT
                )''')
                
    # 3. Colaboradores / Vendedores
    c.execute('''CREATE TABLE IF NOT EXISTS colaboradores (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    nombre TEXT,
                    contacto TEXT,
                    comision_porcentaje REAL
                )''')
                
    conn.commit()
    conn.close()

@app.route("/")
def index():
    conn = sqlite3.connect("db.sqlite3")
    c = conn.cursor()
    c.execute("SELECT * FROM configuracion ORDER BY id DESC LIMIT 1")
    config = c.fetchone()
    
    ocupados = {}
    numeros_lista = []
    if config:
        rifa_id = config[0]
        cifras = config[8]
        
        if cifras == 2:
            numeros_lista = [f"{i:02d}" for i in range(100)]
        elif cifras == 3:
            numeros_lista = [f"{i:03d}" for i in range(1000)]
        elif cifras == 4:
            numeros_lista = [f"{i:04d}" for i in range(10000)]
        else:
            numeros_lista = [f"{i:02d}" for i in range(100)]
            
        c.execute("SELECT numero, estado, nombre FROM apartados WHERE rifa_id = ?", (rifa_id,))
        for row in c.fetchall():
            ocupados[row[0]] = {"estado": row[1], "cliente": row[2]}
            
    conn.close()
    return render_template("index.html", config=config, numeros_lista=numeros_lista, ocupados=ocupados)

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        if request.form["password"] == "1234":
            session["admin"] = True
            return redirect("/admin")
    return render_template("login.html")

@app.route("/admin")
def admin():
    if not session.get("admin"):
        return redirect(url_for("login"))
    
    conn = sqlite3.connect("db.sqlite3")
    c = conn.cursor()
    c.execute("SELECT * FROM configuracion ORDER BY id DESC")
    rifas = c.fetchall()
    c.execute("SELECT * FROM apartados ORDER BY id DESC")
    datos = c.fetchall()
    c.execute("SELECT * FROM colaboradores")
    colaboradores = c.fetchall()
    conn.close()
    return render_template("admin.html", rifas=rifas, datos=datos, colaboradores=colaboradores)

@app.route("/crear_rifa", methods=["POST"])
def crear_rifa():
    if not session.get("admin"):
        return redirect(url_for("login"))
    
    titulo = request.form["titulo"]
    organizador = request.form["organizador"]
    canal_contacto = request.form["canal_contacto"]
    contacto_detalles = request.form["contacto_detalles"]
    lugar_residencia = request.form.get("lugar_residencia", "")
    lugar_juego = request.form.get("lugar_juego", "")
    modalidad = request.form["modalidad"]
    
    if "2" in modalidad:
        cifras = 2
    elif "3" in modalidad:
        cifras = 3
    elif "4" in modalidad:
        cifras = 4
    else:
        cifras = 2

    premio = request.form["premio"]
    moneda = request.form["moneda"]
    tipo_precio = request.form.get("tipo_precio", "Simple")
    
    # Conversión segura de precio base
    try:
        precio_base = float(request.form.get("precio_base", 0))
    except (ValueError, TypeError):
        precio_base = 0.0

    metodos_pago = request.form.get("metodos_pago", "")
    detalles_pago = request.form.get("detalles_pago", "")
    loteria = request.form.get("loteria", "")
    imagen_url = request.form.get("imagen_url", "")
    fecha_sorteo = request.form.get("fecha_sorteo", "")

    conn = sqlite3.connect("db.sqlite3")
    c = conn.cursor()
    c.execute('''INSERT INTO configuracion 
                 (titulo, organizador, canal_contacto, contacto_detalles, lugar_residencia, lugar_juego, modalidad, cifras, premio, moneda, tipo_precio, precio_base, metodos_pago, detalles_pago, loteria, imagen_url, fecha_sorteo)
                 VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
              (titulo, organizador, canal_contacto, contacto_detalles, lugar_residencia, lugar_juego, modalidad, cifras, premio, moneda, tipo_precio, precio_base, metodos_pago, detalles_pago, loteria, imagen_url, fecha_sorteo))
    conn.commit()
    conn.close()
    return redirect(url_for("admin"))

@app.route("/apartar", methods=["POST"])
def apartar():
    rifa_id = request.form.get("rifa_id")
    nombre = request.form.get("nombre", "")
    contacto = request.form.get("contacto", "")
    residencia = request.form.get("residencia", "")
    numero_raw = request.form.get("numero", "").strip()
    vendedor = request.form.get("vendedor", "Directo")
    fecha = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    conn = sqlite3.connect("db.sqlite3")
    c = conn.cursor()
    
    # Traer configuración de la rifa
    c.execute("SELECT cifras, titulo, organizador, canal_contacto, contacto_detalles, moneda, precio_base FROM configuracion WHERE id = ?", (rifa_id,))
    config_rifa = c.fetchone()
    
    if config_rifa:
        cifras = config_rifa[0]
        titulo_rifa = config_rifa[1]
        contacto_soporte = config_rifa[4]
        moneda = config_rifa[5]
        precio_defecto = config_rifa[6]
    else:
        cifras = 2
        titulo_rifa = "Rifa"
        contacto_soporte = ""
        moneda = ""
        precio_defecto = 0.0

    # Conversión blindada a número flotante
    raw_val = request.form.get("valor_pagado", "0")
    try:
        valor_pagado = float(raw_val)
    except (ValueError, TypeError):
        try:
            valor_pagado = float(precio_defecto)
        except (ValueError, TypeError):
            valor_pagado = 0.0

    # Formateo dinámico con ceros a la izquierda
    try:
        numero = f"{int(numero_raw):0{cifras}d}"
    except (ValueError, TypeError):
        numero = numero_raw

    # Validación de número ya ocupado
    c.execute("SELECT estado FROM apartados WHERE rifa_id = ? AND numero = ?", (rifa_id, numero))
    existente = c.fetchone()
    if existente:
        conn.close()
        return f"<script>alert('El número {numero} ya se encuentra apartado o pagado. Por favor elige otro.'); window.history.back();</script>"

    c.execute('''INSERT INTO apartados (rifa_id, nombre, contacto, residencia, numero, valor_pagado, vendedor, estado, fecha)
                 VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)''',
              (rifa_id, nombre, contacto, residencia, numero, valor_pagado, vendedor, "Pendiente", fecha))
    conn.commit()
    conn.close()

    num_wa_clean = ''.join(filter(str.isdigit, str(contacto_soporte)))
    
    mensaje_wa = f"Hola! Acabo de apartar el número *{numero}* para la rifa '{titulo_rifa}'.\n*Nombre:* {nombre}\n*Teléfono:* {contacto}\n*Valor:* {valor_pagado} {moneda}\n*Fecha:* {fecha}"
    mensaje_wa_encoded = urllib.parse.quote(mensaje_wa)

    return render_template("ticket.html", nombre=nombre, contacto=contacto, numero=numero, valor=f"{valor_pagado} {moneda}", fecha=fecha, mensaje_wa_encoded=mensaje_wa_encoded, num_wa_clean=num_wa_clean)

@app.route("/aprobar/<int:id>")
def aprobar(id):
    if not session.get("admin"):
        return redirect(url_for("login"))
    conn = sqlite3.connect("db.sqlite3")
    c = conn.cursor()
    c.execute("UPDATE apartados SET estado = 'Pagado' WHERE id = ?", (id,))
    conn.commit()
    conn.close()
    return redirect(url_for("admin"))

@app.route("/eliminar/<int:id>")
def eliminar(id):
    if not session.get("admin"):
        return redirect(url_for("login"))
    conn = sqlite3.connect("db.sqlite3")
    c = conn.cursor()
    c.execute("DELETE FROM apartados WHERE id = ?", (id,))
    conn.commit()
    conn.close()
    return redirect(url_for("admin"))

@app.route("/agregar_colaborador", methods=["POST"])
def agregar_colaborador():
    if not session.get("admin"):
        return redirect(url_for("login"))
    nombre = request.form["collab_nombre"]
    contacto = request.form["collab_contacto"]
    
    try:
        comision = float(request.form.get("collab_comision", 0))
    except (ValueError, TypeError):
        comision = 0.0

    conn = sqlite3.connect("db.sqlite3")
    c = conn.cursor()
    c.execute("INSERT INTO colaboradores (nombre, contacto, comision_porcentaje) VALUES (?, ?, ?)",
              (nombre, contacto, comision))
    conn.commit()
    conn.close()
    return redirect(url_for("admin"))

import os

if __name__ == "__main__":
    init_db()
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
