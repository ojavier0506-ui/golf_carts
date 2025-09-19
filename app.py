from flask import Flask, render_template, request, jsonify, redirect, url_for, session
import json
import os
from datetime import datetime

app = Flask(__name__)
app.secret_key = "super_secret_key"  # Necesario para manejar sesiones (puede ser cualquier string)

# Lista de 40 carritos SunCart
carts = [f"SunCart {i+1}" for i in range(40)]

# Opciones de estado (con "Unassigned" como categoría inicial)
status_options = [
    "Unassigned",
    "Charging",
    "Ready for Walk up",
    "Being used by Guest",
    "Out of Service",
    "Other"
]

# Ruta del archivo en el disco persistente
PERSISTENT_PATH = "/persistent"
DATA_FILE = os.path.join(PERSISTENT_PATH, "data.json")
HISTORY_FILE = os.path.join(PERSISTENT_PATH, "history.json")
os.makedirs(PERSISTENT_PATH, exist_ok=True)

# Cargar o crear archivo persistente (estado actual)
if os.path.exists(DATA_FILE):
    with open(DATA_FILE, "r") as f:
        cart_states = json.load(f)
else:
    cart_states = {cart: {"status": "Unassigned", "comment": ""} for cart in carts}
    with open(DATA_FILE, "w") as f:
        json.dump(cart_states, f)

# Cargar o crear archivo de historial
if os.path.exists(HISTORY_FILE):
    with open(HISTORY_FILE, "r") as f:
        history = json.load(f)
else:
    history = {cart: [] for cart in carts}
    with open(HISTORY_FILE, "w") as f:
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


# --- APP PRINCIPAL ---
@app.route('/', methods=['GET', 'POST'])
def index():
    global cart_states, history

    if not session.get('logged_in'):
        return redirect(url_for("login"))

    if request.method == 'POST':
        # Procesar todos los carritos y registrar cambios SOLO si hay diferencia
        for cart in carts:
            status = request.form.get(f"status_{cart}")
            comment = request.form.get(f"comment_{cart}", "")[:200]  # limitar longitud comentario

            # Seguridad básica: si el estado no es válido, mandar a Unassigned
            if status not in status_options:
                status = "Unassigned"

            prev_status = cart_states.get(cart, {}).get("status", "Unassigned")
            prev_comment = cart_states.get(cart, {}).get("comment", "")

            # Si hubo algún cambio (status o comentario), registrar en historial
            if status != prev_status or comment != prev_comment:
                now = datetime.now()
                date_str = now.strftime("%Y-%m-%d")
                time_str = now.strftime("%H:%M:%S")

                entry = {
                    "date": date_str,
                    "time": time_str
                }

                # Determinar tipo de cambio
                if status != prev_status and comment != prev_comment:
                    entry["change"] = "Status+Comment"
                    entry["details"] = f"{prev_status} → {status}"
                    # comment action
                    if prev_comment == "" and comment != "":
                        entry["comment_action"] = "Added"
                    elif prev_comment != "" and comment == "":
                        entry["comment_action"] = "Deleted"
                    elif prev_comment != comment:
                        entry["comment_action"] = "Edited"
                    else:
                        entry["comment_action"] = None

                    entry["comment_text"] = comment

                elif status != prev_status:
                    entry["change"] = "Status"
                    entry["details"] = f"{prev_status} → {status}"
                    # si también hay cambio de comentario será manejado en la rama anterior

                elif comment != prev_comment:
                    entry["change"] = "Comment"
                    # determinar acción de comentario
                    if prev_comment == "" and comment != "":
                        entry["comment_action"] = "Added"
                    elif prev_comment != "" and comment == "":
                        entry["comment_action"] = "Deleted"
                    elif prev_comment != comment:
                        entry["comment_action"] = "Edited"
                    else:
                        entry["comment_action"] = None

                    entry["comment_text"] = comment

                # Asegurar que la lista exista
                if cart not in history:
                    history[cart] = []

                # Insertar al inicio para ver lo más reciente primero
                history[cart].insert(0, entry)

            # Actualizar estado actual
            cart_states[cart] = {"status": status, "comment": comment}

        # Guardar cambios en disco (estados + historial)
        with open(DATA_FILE, "w") as f:
            json.dump(cart_states, f)

        with open(HISTORY_FILE, "w") as f:
            json.dump(history, f)

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
        return jsonify([])  # no permitir acceso si no está logueado
    result = [cart for cart in carts if cart_states[cart]["status"] == status]
    return jsonify(result)


# Página de historial (renderiza la UI)
@app.route('/history')
def history_page():
    if not session.get('logged_in'):
        return redirect(url_for("login"))
    return render_template("history.html", carts=carts)


# API para obtener historial filtrado (por carrito y opcional por fecha)
@app.route('/api/history')
def api_history():
    if not session.get('logged_in'):
        return jsonify([])

    cart = request.args.get('cart')
    date = request.args.get('date')  # formato YYYY-MM-DD (opcional)

    if not cart or cart not in history:
        return jsonify([])

    entries = history.get(cart, [])
    if date:
        filtered = [e for e in entries if e.get("date") == date]
    else:
        filtered = entries

    return jsonify(filtered)


if __name__ == "__main__":
    app.run(debug=True)
