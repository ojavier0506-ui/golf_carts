from flask import Flask, render_template, request, jsonify, redirect, url_for, session
import json
import os

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

            # Seguridad básica: si el estado no es válido, mandar a Unassigned
            if status not in status_options:
                status = "Unassigned"

            cart_states[cart]["status"] = status
            cart_states[cart]["comment"] = comment[:200]  # limitar longitud comentario

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
        return jsonify([])  # no permitir acceso si no está logueado
    result = [cart for cart in carts if cart_states[cart]["status"] == status]
    return jsonify(result)


if __name__ == "__main__":
    app.run(debug=True)