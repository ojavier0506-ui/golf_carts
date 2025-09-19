from flask import Flask, render_template, request, jsonify, redirect, url_for, session, send_file
import json
import os
import datetime
from io import BytesIO
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib import colors
from reportlab.platypus import Table, TableStyle

app = Flask(__name__)
app.secret_key = "super_secret_key"  # Necesario para manejar sesiones

# Lista de 40 carritos SunCart
carts = [f"SunCart {i+1}" for i in range(40)]

# Opciones de estado
status_options = [
    "Unassigned",
    "Charging",
    "Ready for Walk up",
    "Being used by Guest",
    "Out of Service",
    "Other"
]

# Ruta del archivo persistente
PERSISTENT_PATH = "/persistent"
DATA_FILE = os.path.join(PERSISTENT_PATH, "data.json")
os.makedirs(PERSISTENT_PATH, exist_ok=True)

# Cargar o crear archivo persistente
if os.path.exists(DATA_FILE):
    with open(DATA_FILE, "r") as f:
        cart_states = json.load(f)
else:
    cart_states = {cart: {"status": "Unassigned", "comment": ""} for cart in carts}
    with open(DATA_FILE, "w") as f:
        json.dump(cart_states, f)


# --- LOGIN ---
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get("username")
        password = request.form.get("password")

        if username == "Oscar" and password == "3280":
            session['logged_in'] = True
            return redirect(url_for("index"))
        else:
            return render_template("login.html", error="Invalid credentials")

    return render_template("login.html")


@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for("login"))


# --- APP PRINCIPAL ---
@app.route('/', methods=['GET', 'POST'])
def index():
    global cart_states

    if not session.get('logged_in'):
        return redirect(url_for("login"))

    if request.method == 'POST':
        for cart in carts:
            status = request.form.get(f"status_{cart}")
            comment = request.form.get(f"comment_{cart}", "")

            # Seguridad básica
            if status not in status_options:
                status = "Unassigned"

            cart_states[cart]["status"] = status
            cart_states[cart]["comment"] = comment[:200]

        with open(DATA_FILE, "w") as f:
            json.dump(cart_states, f)

    # Contar carritos en cada categoría
    counts = {option: 0 for option in status_options}
    for cart in carts:
        state = cart_states[cart]["status"]
        if state not in status_options:
            state = "Unassigned"
            cart_states[cart]["status"] = state
        counts[state] += 1

    return render_template("index.html", carts=carts, status_options=status_options,
                           cart_states=cart_states, counts=counts)


# Endpoint para obtener los carritos de una categoría (AJAX)
@app.route('/category/<status>')
def category(status):
    if not session.get('logged_in'):
        return jsonify([])
    result = [cart for cart in carts if cart_states[cart]["status"] == status]
    return jsonify(result)


# --- NUEVA RUTA PARA GENERAR PDF ---
@app.route('/report')
def generate_report():
    if not session.get('logged_in'):
        return redirect(url_for("login"))

    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter

    # Título
    c.setFont("Helvetica-Bold", 16)
    c.drawString(50, height - 50, "GOLF CART REPORT")

    # Fecha y hora
    now = datetime.datetime.now()
    c.setFont("Helvetica", 10)
    c.drawString(50, height - 70, f"Fecha: {now.strftime('%Y-%m-%d %H:%M:%S')}")

    # Resumen de categorías
    y = height - 100
    c.setFont("Helvetica-Bold", 12)
    c.drawString(50, y, "Resumen de Estados:")
    y -= 15
    counts = {option: sum(1 for cart in carts if cart_states[cart]['status'] == option) for option in status_options}
    for status, count in counts.items():
        c.setFont("Helvetica", 10)
        c.drawString(60, y, f"{status}: {count}")
        y -= 15

    # Tabla de carritos
    data = [["Carrito", "Estado", "Comentario"]]
    for cart in carts:
        data.append([cart, cart_states[cart]["status"], cart_states[cart]["comment"]])

    table = Table(data, colWidths=[100, 150, 250])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.grey),
        ('TEXTCOLOR',(0,0),(-1,0),colors.whitesmoke),
        ('ALIGN',(0,0),(-1,-1),'LEFT'),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,-1), 10),
        ('BOTTOMPADDING', (0,0), (-1,0), 6),
        ('GRID', (0,0), (-1,-1), 0.5, colors.black),
    ]))

    table.wrapOn(c, width, height)
    table.drawOn(c, 50, y - len(data)*18)

    c.showPage()
    c.save()
    buffer.seek(0)
    return send_file(buffer, as_attachment=True, download_name="GolfCartReport.pdf", mimetype='application/pdf')


if __name__ == "__main__":
    app.run(debug=True)
