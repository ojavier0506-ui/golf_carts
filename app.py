from flask import Flask, render_template, request, jsonify, redirect, url_for, session, send_file, abort
import json
import os
from datetime import datetime
from zoneinfo import ZoneInfo
from io import BytesIO
from fpdf import FPDF
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps

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
    "Returned",               
    "Reserved for Pick-Up",
    "Other"
]

# Archivos de datos
PERSISTENT_PATH = "/persistent"
DATA_FILE = os.path.join(PERSISTENT_PATH, "data.json")
HISTORY_FILE = os.path.join(PERSISTENT_PATH, "history.json")
USERS_FILE = os.path.join(PERSISTENT_PATH, "users.json")
os.makedirs(PERSISTENT_PATH, exist_ok=True)

def atomic_write_json(path, obj):
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)

# Cargar/crear estados
if os.path.exists(DATA_FILE):
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        cart_states = json.load(f)
else:
    cart_states = {cart: {"status": "Unassigned", "comment": ""} for cart in carts}
    atomic_write_json(DATA_FILE, cart_states)

# Cargar/crear historial
if os.path.exists(HISTORY_FILE):
    with open(HISTORY_FILE, "r", encoding="utf-8") as f:
        history_log = json.load(f)
else:
    history_log = {cart: [] for cart in carts}
    atomic_write_json(HISTORY_FILE, history_log)

# Cargar/crear usuarios (seed admin)
def load_or_seed_users():
    if os.path.exists(USERS_FILE):
        with open(USERS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    users_seed = {
        "Oscar": {
            "password_hash": generate_password_hash("3280"),
            "role": "admin"
        }
    }
    atomic_write_json(USERS_FILE, users_seed)
    return users_seed

users = load_or_seed_users()

# Helpers de auth
def login_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if not session.get('logged_in'):
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return wrapper

def admin_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if not session.get('logged_in'):
            return redirect(url_for("login"))
        if session.get('role') != 'admin':
            return abort(403)
        return f(*args, **kwargs)
    return wrapper

# --- LOGIN ---
@app.route('/login', methods=['GET', 'POST'])
def login():
    global users
    if request.method == 'POST':
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        user = users.get(username)
        if user and check_password_hash(user["password_hash"], password):
            session['logged_in'] = True
            session['username'] = username
            session['role'] = user.get("role", "user")
            return redirect(url_for("index"))
        else:
            return render_template("login.html", error="Invalid credentials")

    return render_template("login.html")

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for("login"))

# --- HOME ---
@app.route('/')
@login_required
def index():
    counts = {option: 0 for option in status_options}
    for cart in carts:
        counts[cart_states[cart]["status"]] += 1

    return render_template("index.html",
                           carts=carts,
                           status_options=status_options,
                           counts=counts)

# --- API: Obtener datos de un carrito (ahora incluye último cambio) ---
@app.route('/cart/<cart_name>')
@login_required
def get_cart(cart_name):
    state = cart_states.get(cart_name, {"status": "Unassigned", "comment": ""})
    # Buscar el último cambio (si existe) en el historial de ese carrito
    entries = history_log.get(cart_name, [])
    last_change = None
    if entries:
        last = entries[-1]
        last_change = {
            "user": last.get("user", "Unknown"),
            "date": last.get("date", ""),
            "time": last.get("time", ""),
            "change_type": last.get("change_type", "")
        }
    return jsonify({
        "status": state.get("status", "Unassigned"),
        "comment": state.get("comment", ""),
        "last_change": last_change
    })

# --- API: Guardar cambios de un carrito ---
@app.route('/update_cart', methods=['POST'])
@login_required
def update_cart():
    global cart_states, history_log

    cart = request.form.get("cart")
    status = request.form.get("status")
    comment = request.form.get("comment", "")[:200]

    if cart not in carts:
        return jsonify({"success": False})

    if status not in status_options:
        status = "Unassigned"

    now = datetime.now(ZoneInfo("America/New_York"))
    old_status = cart_states[cart]["status"]
    old_comment = cart_states[cart]["comment"]
    actor = session.get("username", "Unknown")

    if old_status != status:
        history_log[cart].append({
            "date": now.strftime("%Y-%m-%d"),
            "time": now.strftime("%H:%M:%S"),
            "change_type": "Status changed",
            "old_value": old_status,
            "new_value": status,
            "comment": comment,
            "user": actor
        })

    if old_comment != comment:
        history_log[cart].append({
            "date": now.strftime("%Y-%m-%d"),
            "time": now.strftime("%H:%M:%S"),
            "change_type": "Comment updated",
            "old_value": old_comment,
            "new_value": comment,
            "comment": comment,
            "user": actor
        })

    cart_states[cart]["status"] = status
    cart_states[cart]["comment"] = comment

    atomic_write_json(DATA_FILE, cart_states)
    atomic_write_json(HISTORY_FILE, history_log)

    # Recalcular conteos
    counts = {option: 0 for option in status_options}
    for c in carts:
        counts[cart_states[c]["status"]] += 1

    return jsonify({"success": True, "counts": counts})

# --- CATEGORY AJAX ---
@app.route('/category/<status>')
@login_required
def category(status):
    result = [
        {"cart": cart, "comment": cart_states[cart]["comment"]}
        for cart in carts if cart_states[cart]["status"] == status
    ]
    return jsonify(result)

# --- HISTORY PAGE ---
@app.route('/history')
@login_required
def history():
    return render_template("history.html", carts=carts)

@app.route('/history/<cart_name>')
@login_required
def get_cart_history(cart_name):
    return jsonify(history_log.get(cart_name, []))

# --- REPORT PDF ---
@app.route('/report')
@login_required
def report():
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", "B", 16)
    pdf.cell(0, 10, "SunCart Report", ln=True, align="C")
    pdf.ln(10)

    # Conteo
    counts = {option: 0 for option in status_options}
    for cart in carts:
        counts[cart_states[cart]["status"]] += 1

    pdf.set_font("Arial", "", 12)
    for status, count in counts.items():
        pdf.cell(0, 8, f"{status}: {count}", ln=True)
    pdf.ln(5)

    # Tabla
    pdf.set_font("Arial", "B", 12)
    pdf.cell(50, 8, "Cart", 1)
    pdf.cell(50, 8, "Status", 1)
    pdf.cell(90, 8, "Comment", 1, ln=True)

    pdf.set_font("Arial", "", 12)
    for cart in carts:
        pdf.cell(50, 8, cart, 1)
        pdf.cell(50, 8, cart_states[cart]["status"], 1)
        pdf.cell(90, 8, cart_states[cart]["comment"][:45], 1, ln=True)

    now = datetime.now(ZoneInfo("America/New_York"))
    filename = now.strftime("SunCarts_%Y-%m-%d.pdf")

    pdf_bytes = BytesIO(pdf.output(dest='S').encode('latin1'))
    pdf_bytes.seek(0)
    return send_file(pdf_bytes, download_name=filename, as_attachment=True)

# --- ADMIN (sigue igual que lo tenías) ---
@app.route('/admin/users', methods=['GET'])
@admin_required
def admin_users():
    return render_template("admin_users.html", users=users)

@app.route('/admin/users', methods=['POST'])
@admin_required
def admin_users_post():
    global users

    action = request.form.get("action")

    if action == "add":
        new_username = (request.form.get("username") or "").strip()
        new_password = request.form.get("password") or ""
        role = request.form.get("role") or "user"

        if not new_username or not new_password:
            return render_template("admin_users.html", users=users, error="Username and password are required")

        if new_username in users:
            return render_template("admin_users.html", users=users, error="User already exists")

        if role not in ("admin", "user"):
            role = "user"

        users[new_username] = {
            "password_hash": generate_password_hash(new_password),
            "role": role
        }
        atomic_write_json(USERS_FILE, users)
        return redirect(url_for("admin_users"))

    elif action == "delete":
        del_username = request.form.get("username") or ""
        if del_username in users:
            if del_username == session.get("username"):
                return render_template("admin_users.html", users=users, error="You cannot delete yourself while logged in.")
            admins = [u for u, info in users.items() if info.get("role") == "admin"]
            if users[del_username].get("role") == "admin" and len(admins) <= 1:
                return render_template("admin_users.html", users=users, error="At least one admin is required.")
            del users[del_username]
            atomic_write_json(USERS_FILE, users)
        return redirect(url_for("admin_users"))

    elif action == "edit":
        old_username = (request.form.get("old_username") or "").strip()
        new_username = (request.form.get("username") or "").strip()
        new_password = request.form.get("password") or ""
        role = request.form.get("role") or "user"

        if old_username not in users:
            return render_template("admin_users.html", users=users, error="Original user not found")

        if not new_username:
            return render_template("admin_users.html", users=users, error="Username cannot be empty")

        if users[old_username].get("role") == "admin" and role != "admin":
            admins = [u for u, info in users.items() if info.get("role") == "admin"]
            if len(admins) <= 1:
                return render_template("admin_users.html", users=users, error="At least one admin must remain.")

        if new_username != old_username and new_username in users:
            return render_template("admin_users.html", users=users, error="Another user already has that username")

        updated = {
            "password_hash": users[old_username]["password_hash"],
            "role": role if role in ("admin", "user") else users[old_username].get("role", "user")
        }
        if new_password:
            updated["password_hash"] = generate_password_hash(new_password)

        if new_username != old_username:
            users[new_username] = updated
            del users[old_username]
            if session.get("username") == old_username:
                session["username"] = new_username
                session["role"] = updated["role"]
        else:
            users[old_username] = updated
            if session.get("username") == old_username:
                session["role"] = updated["role"]

        atomic_write_json(USERS_FILE, users)
        return redirect(url_for("admin_users"))

    else:
        return render_template("admin_users.html", users=users, error="Invalid action")

@app.errorhandler(403)
def forbidden(_):
    return render_template("login.html", error="Forbidden: admin only"), 403

if __name__ == "__main__":
    app.run(debug=True)
