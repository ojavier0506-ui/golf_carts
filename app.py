from flask import Flask, render_template, request, redirect, url_for, session, send_file
from datetime import datetime
import json
import os
from fpdf import FPDF
import io
import pytz

app = Flask(__name__)
app.secret_key = "super_secret_key"

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

# Archivos persistentes
PERSISTENT_PATH = "/persistent"
os.makedirs(PERSISTENT_PATH, exist_ok=True)
DATA_FILE = os.path.join(PERSISTENT_PATH, "data.json")
HISTORY_FILE = os.path.join(PERSISTENT_PATH, "history.json")

# Cargar datos
if os.path.exists(DATA_FILE):
    with open(DATA_FILE, "r") as f:
        cart_states = json.load(f)
else:
    cart_states = {cart: {"status": "Unassigned", "comment": ""} for cart in carts}
    with open(DATA_FILE, "w") as f:
        json.dump(cart_states, f)

if os.path.exists(HISTORY_FILE):
    with open(HISTORY_FILE, "r") as f:
        history_data = json.load(f)
else:
    history_data = []
    with open(HISTORY_FILE, "w") as f:
        json.dump(history_data, f)

# --- LOGIN ---
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get("username").strip()
        password = request.form.get("password").strip()
        if username.lower() == "oscar" and password == "3280":
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
    global cart_states, history_data

    if not session.get('logged_in'):
        return redirect(url_for("login"))

    if request.method == 'POST':
        cart = request.form.get("selected_cart")
        status = request.form.get("status")
        comment = request.form.get("comment", "")[:200]

        # Guardar historial si hay cambios
        old_status = cart_states[cart]["status"]
        old_comment = cart_states[cart]["comment"]
        changes = []

        if status != old_status:
            changes.append({"change_type": "Status Change", "from": old_status, "to": status})
        if comment != old_comment:
            changes.append({"change_type": "Comment Change", "from": old_comment, "to": comment})

        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        for c in changes:
            history_data.append({
                "cart": cart,
                "timestamp": timestamp,
                "change": c["change_type"],
                "from": c["from"],
                "to": c["to"]
            })

        cart_states[cart]["status"] = status
        cart_states[cart]["comment"] = comment

        # Guardar en disco
        with open(DATA_FILE, "w") as f:
            json.dump(cart_states, f)
        with open(HISTORY_FILE, "w") as f:
            json.dump(history_data, f)

    counts = {option: 0 for option in status_options}
    for cart in carts:
        state = cart_states[cart]["status"]
        if state not in status_options:
            state = "Unassigned"
            cart_states[cart]["status"] = state
        counts[state] += 1

    return render_template("index.html", carts=carts, cart_states=cart_states,
                           status_options=status_options, counts=counts)

# --- Historial ---
@app.route('/history', methods=['GET', 'POST'])
def history():
    if not session.get('logged_in'):
        return redirect(url_for("login"))

    selected_cart = None
    selected_date = None
    filtered_history = []

    if request.method == 'POST':
        selected_cart = request.form.get("cart_filter")
        selected_date = request.form.get("date_filter")
        for h in history_data:
            if (not selected_cart or h["cart"] == selected_cart) and \
               (not selected_date or h["timestamp"].startswith(selected_date)):
                filtered_history.append(h)

    return render_template("history.html", carts=carts,
                           history=filtered_history,
                           selected_cart=selected_cart,
                           selected_date=selected_date)

# --- PDF Report ---
@app.route('/report')
def report():
    if not session.get('logged_in'):
        return redirect(url_for("login"))

    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", "B", 14)
    pdf.cell(0, 10, "SunCarts Report", ln=True, align="C")
    pdf.ln(5)

    # Conteo por estado
    pdf.set_font("Arial", "", 12)
    for status in status_options:
        count = sum(1 for c in carts if cart_states[c]["status"] == status)
        pdf.cell(0, 8, f"{status}: {count}", ln=True)
    pdf.ln(5)

    # Tabla de carritos
    pdf.set_font("Arial", "B", 12)
    pdf.cell(50, 8, "Carrito", 1)
    pdf.cell(50, 8, "Status", 1)
    pdf.cell(90, 8, "Comment", 1, ln=True)

    pdf.set_font("Arial", "", 12)
    for cart in carts:
        pdf.cell(50, 8, cart, 1)
        pdf.cell(50, 8, cart_states[cart]["status"], 1)
        comment = cart_states[cart]["comment"][:45]  # Ajustar ancho
        pdf.cell(90, 8, comment, 1, ln=True)

    # Nombre con fecha actual
    tz = pytz.timezone("America/New_York")
    filename = f"SunCarts_{datetime.now(tz).strftime('%Y-%m-%d')}.pdf"

    output = io.BytesIO()
    pdf.output(output)
    output.seek(0)

    return send_file(output, download_name=filename, as_attachment=True)

if __name__ == "__main__":
    app.run(debug=True)
