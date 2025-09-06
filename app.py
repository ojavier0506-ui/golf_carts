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

# Ruta del archivo en el disco persistente
PERSISTENT_PATH = "/persistent"
DATA_FILE = os.path.join(PERSISTENT_PATH, "data.json")
HISTORY_FILE = os.path.join(PERSISTENT_PATH, "history.json")

# Asegurarse de que el directorio exista
os.makedirs(PERSISTENT_PATH, exist_ok=True)

# Cargar datos actuales
if os.path.exists(DATA_FILE):
    with open(DATA_FILE, "r") as f:
        cart_states = json.load(f)
else:
    cart_states = {cart: {"status": "Ready for Walk up", "comment": ""} for cart in carts}
    with open(DATA_FILE, "w") as f:
        json.dump(cart_states, f)

# Cargar historial
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

    if request.method == 'POST':
        for cart in carts:
            new_status = request.form.get(f"status_{cart}")
            new_comment = request.form.get(f"comment_{cart}")
            if new_status != cart_states[cart]["status"] or new_comment != cart_states[cart]["comment"]:
                # Guardar en historial
                history[cart].append({
                    "time": datetime.now().isoformat(),
                    "status": new_status,
                    "comment": new_comment
                })
            cart_states[cart]["status"] = new_status
            cart_states[cart]["comment"] = new_comment

        # Guardar siempre
        with open(DATA_FILE, "w") as f:
            json.dump(cart_states, f)
        with open(HISTORY_FILE, "w") as f:
            json.dump(history, f)
        return jsonify({"message": "Changes saved!"})

    # Contar carritos en cada categoría
    counts = {option: 0 for option in status_options}
    for cart in carts:
        counts[cart_states[cart]["status"]] += 1

    return render_template("index.html", carts=carts, status_options=status_options,
                           cart_states=cart_states, counts=counts)

@app.route('/get_cart_history_events', methods=['POST'])
def get_cart_history_events():
    cart = request.form.get('cart')
    if not cart or cart not in history:
        return jsonify([])
    events = []
    for item in history[cart]:
        events.append({
            "title": f"{item['status']}",
            "start": item['time'],
            "extendedProps": {"comment": item['comment']}
        })
    return jsonify(events)

if __name__ == "__main__":
    app.run(debug=True)
