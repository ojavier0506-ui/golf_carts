from flask import Flask, render_template, request, jsonify, redirect, url_for, session, send_file
import json
import os
from datetime import datetime
from zoneinfo import ZoneInfo
from io import BytesIO
from fpdf import FPDF

app = Flask(__name__)
app.secret_key = "super_secret_key"

# Lista de carritos
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

# Archivos de datos
PERSISTENT_PATH = "/persistent"
DATA_FILE = os.path.join(PERSISTENT_PATH, "data.json")
HISTORY_FILE = os.path.join(PERSISTENT_PATH, "history.json")
os.makedirs(PERSISTENT_PATH, exist_ok=True)

# Cargar o crear datos
if os.path.exists(DATA_FILE):
    with open(DATA_FILE, "r") as f:
        cart_states = json.load(f)
else:
    cart_states = {cart: {"status": "Unassigned", "comment": ""} for cart in carts}
    with open(DATA_FILE, "w") as f:
        json.dump(cart_states, f)

if os.path.exists(HISTORY_FILE):
    with open(HISTORY_FILE, "r") as f:
        history_log = json.load(f)
else:
    history_log = {cart: [] for cart in carts}
    with open(HISTORY_FILE, "w") as f:
        json.dump(history_log, f)

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
    global cart_states, history_log

    if not session.get('logged_in'):
        return redirect(url_for("login"))

    if request.method == 'POST':
        for cart in carts:
            status = request.form.get(f"status_{cart}")
            comment = request.form.get(f"comment_{cart}", "")

            if status not in status_options:
                status = "Unassigned"

            now = datetime.now(ZoneInfo("America/New_York"))
            old_status = cart_states[cart]["status"]
            old_comment = cart_states[cart]["comment"]

            if old_status != status:
                history_log[cart].append({
                    "date": now.strftime("%Y-%m-%d"),
                    "time": now.strftime("%H:%M:%S"),
                    "change_type": "Status changed",
                    "old_value": old_status,
                    "new_value": status,
                    "comment": comment
                })

            if old_comment != comment:
                history_log[cart].append({
                    "date": now.strftime("%Y-%m-%d"),
                    "time": now.strftime("%H:%M:%S"),
                    "change_type": "Comment updated",
                    "old_value": old_comment,
                    "new_value": comment,
                    "comment": comment
                })

            cart_states[cart]["status"] = status
            cart_states[cart]["comment"] = comment[:200]

        with open(DATA_FILE, "w") as f:
            json.dump(cart_states, f)
        with open(HISTORY_FILE, "w") as f:
            json.dump(history_log, f)

        # Recalcular conteos
        counts = {option: 0 for option in status_options}
        for cart in carts:
            counts[cart_states[cart]["status"]] += 1

        # 👉 devolver JSON si es fetch
        if request.headers.get("X-Requested-With") == "fetch":
            return jsonify({"success": True, "counts": counts})

    counts = {option: 0 for option in status_options}
    for cart in carts:
        counts[cart_states[cart]["status"]] += 1

    return render_template("index.html", carts=carts, status_options=status_options,
                           cart_states=cart_states, counts=counts)
