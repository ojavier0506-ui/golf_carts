from flask import Flask, render_template, request, jsonify
import json
import os
from datetime import datetime

app = Flask(__name__)

# Lista de 40 SunCarts
carts = [f"SunCart {i+1}" for i in range(40)]

# Opciones de estado
status_options = [
    "Charging",
    "Ready for Walk up",
    "Being used by Guest",
    "Out of Service",
    "Other"
]

# Ruta del disco persistente
PERSISTENT_PATH = "/persistent"
DATA_FILE = os.path.join(PERSISTENT_PATH, "data.json")
HISTORY_FILE = os.path.join(PERSISTENT_PATH, "history.json")

# Crear carpeta si no existe
os.makedirs(PERSISTENT_PATH, exist_ok=True)

# Cargar o inicializar cart_states
if os.path.exists(DATA_FILE):
    with open(DATA_FILE, "r") as f:
        cart_states = json.load(f)
else:
    cart_states = {cart: {"status": "Ready for Walk up", "comment": ""} for cart in carts}
    with open(DATA_FILE, "w") as f:
        json.dump(cart_states, f)

# Cargar o inicializar historial
if os.path.exists(HISTORY_FILE):
    with open(HISTORY_FILE, "r") as f:
        history = json.load(f)
else:
    history = {cart: [] for cart in carts}
    with open(HISTORY_FILE, "w") as f:
        json.dump(history, f)

@app.route('/', methods=['GET', 'POST'])
def index():
    global cart_states, history

    message = ""
    if request.method == 'POST':
        for cart in carts:
            new_status = request.form.get(f"status_{cart}")
            new_comment = request.form.get(f"comment_{cart}")

            # Guardar historial si hay cambio
            if cart_states[cart]["status"] != new_status or cart_states[cart]["comment"] != new_comment:
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                history[cart].append({
                    "time": timestamp,
                    "status": new_status,
                    "comment": new_comment
                })

            cart_states[cart]["status"] = new_status
            cart_states[cart]["comment"] = new_comment

        # Guardar en disco persistente
        with open(DATA_FILE, "w") as f:
            json.dump(cart_states, f)
        with open(HISTORY_FILE, "w") as f:
            json.dump(history, f)

        message = "Changes saved!"

    # Contar carritos por categoría
    counts = {option: 0 for option in status_options}
    for cart in carts:
        counts[cart_states[cart]["status"]] += 1

    return render_template("index.html", carts=carts, status_options=status_options,
                           cart_states=cart_states, counts=counts, message=message)

@app.route('/get_history', methods=['POST'])
def get_history():
    selected_cart = request.form.get("cart")
    selected_date = request.form.get("date")  # formato YYYY-MM-DD

    if selected_cart not in history:
        return jsonify({"error": "Cart not found"})

    # Filtrar historial por fecha
    filtered = [h for h in history[selected_cart] if h["time"].startswith(selected_date)]
    return jsonify(filtered)

if __name__ == "__main__":
    app.run(debug=True)
