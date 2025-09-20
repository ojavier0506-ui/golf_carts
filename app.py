from flask import Flask, render_template, request, jsonify, redirect, url_for, session, send_file
import json
import os
from datetime import datetime
from io import BytesIO
from fpdf import FPDF

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
DATA_FILE = os.path.join(PERSISTENT_PATH, "data.json")
LOG_FILE = os.path.join(PERSISTENT_PATH, "history.json")
os.makedirs(PERSISTENT_PATH, exist_ok=True)

# Cargar estado inicial
if os.path.exists(DATA_FILE):
    with open(DATA_FILE, "r") as f:
        cart_states = json.load(f)
else:
    cart_states = {cart: {"status": "Unassigned", "comment": ""} for cart in carts}
    with open(DATA_FILE, "w") as f:
        json.dump(cart_states, f)

# Cargar historial
if os.path.exists(LOG_FILE):
    with open(LOG_FILE, "r") as f:
        history = json.load(f)
else:
    history = []
    with open(LOG_FILE, "w") as f:
        json.dump(history, f)


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


# --- PÁGINA PRINCIPAL ---
@app.route('/')
def index():
    if not session.get('logged_in'):
        return redirect(url_for("login"))

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


# --- ACTUALIZAR SOLO UN CARRITO ---
@app.route('/update_cart', methods=['POST'])
def update_cart():
    if not session.get('logged_in'):
        return jsonify({"error": "Not logged in"}), 403

    cart = request.form.get("cart")
    status = request.form.get("status")
    comment = request.form.get("comment", "")

    if cart not in carts:
        return jsonify({"error": "Invalid cart"}), 400

    if status not in status_options:
        status = "Unassigned"

    old_status = cart_states[cart]["status"]
    old_comment = cart_states[cart]["comment"]

    cart_states[cart]["status"] = status
    cart_states[cart]["comment"] = comment[:200]

    # Guardar cambios
    with open(DATA_FILE, "w") as f:
        json.dump(cart_states, f)

    # Guardar log
    change = {}
    if old_status != status:
        change["status_change"] = f"{old_status} → {status}"
    if old_comment != comment:
        change["comment_change"] = f"{old_comment} → {comment}"

    if change:
        history.append({
            "cart": cart,
            "datetime": datetime.now().isoformat(),
            "changes": change
        })
        with open(LOG_FILE, "w") as f:
            json.dump(history, f)

    # Recalcular conteo
    counts = {option: 0 for option in status_options}
    for c in carts:
        counts[cart_states[c]["status"]] += 1

    return jsonify({"success": True, "counts": counts})


# --- REPORT PDF ---
@app.route('/report')
def report():
    if not session.get('logged_in'):
        return redirect(url_for("login"))

    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", "B", 16)
    pdf.cell(200, 10, "SunCarts Report", ln=True, align="C")

    # Resumen
    pdf.set_font("Arial", "", 12)
    counts = {option: 0 for option in status_options}
    for cart in carts:
        counts[cart_states[cart]["status"]] += 1

    pdf.ln(10)
    pdf.cell(200, 10, "Summary:", ln=True)
    for status, count in counts.items():
        pdf.cell(200, 10, f"{status}: {count}", ln=True)

    # Tabla de carritos
    pdf.ln(10)
    pdf.set_font("Arial", "B", 12)
    pdf.cell(60, 10, "Cart", 1)
    pdf.cell(60, 10, "Status", 1)
    pdf.cell(70, 10, "Comment", 1, ln=True)

    pdf.set_font("Arial", "", 10)
    for cart in carts:
        pdf.cell(60, 10, cart, 1)
        pdf.cell(60, 10, cart_states[cart]["status"], 1)
        comment = cart_states[cart]["comment"][:40]
        pdf.cell(70, 10, comment, 1, ln=True)

    buffer = BytesIO()
    pdf.output(buffer, "F")
    buffer.seek(0)

    filename = f"SunCarts_{datetime.now().strftime('%Y-%m-%d')}.pdf"
    return send_file(buffer, as_attachment=True, download_name=filename, mimetype="application/pdf")


# --- CATEGORY FILTER (para el modal) ---
@app.route('/category/<status>')
def category(status):
    if not session.get('logged_in'):
        return jsonify([])
    result = [cart for cart in carts if cart_states[cart]["status"] == status]
    return jsonify(result)


# --- HISTORIAL ---
@app.route('/history')
def history_page():
    if not session.get('logged_in'):
        return redirect(url_for("login"))
    return render_template("history.html", carts=carts)


@app.route('/get_history')
def get_history():
    if not session.get('logged_in'):
        return jsonify([])
    cart = request.args.get("cart")
    date = request.args.get("date")
    result = []

    for entry in history:
        if cart and entry["cart"] != cart:
            continue
        if date and not entry["datetime"].startswith(date):
            continue
        result.append(entry)
    return jsonify(result)


if __name__ == "__main__":
    app.run(debug=True)
