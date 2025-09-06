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

# Disco persistente
PERSISTENT_PATH = "/persistent"
DATA_FILE = os.path.join(PERSISTENT_PATH, "data.json")
HISTORY_FILE = os.path.join(PERSISTENT_PATH, "history.json")

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
        history_data = json.load(f)
else:
    history_data = {cart: [] for cart in carts}
    with open(HISTORY_FILE, "w") as f:
        json.dump(history_data, f)

@app.route('/', methods=['GET', 'POST'])
def index():
    global cart_states, history_data
    if request.method == 'POST':
        for cart in carts:
            status = request.form.get(f"status_{cart}")
            comment = request.form.get(f"comment_{cart}")
            cart_states[cart]["status"] = status
            cart_states[cart]["comment"] = comment

            # Guardar historial con timestamp
            history_entry = {
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "status": status,
                "comment": comment
            }
            history_data[cart].append(history_entry)

        # Guardar en disco
        with open(DATA_FILE, "w") as f:
            json.dump(cart_states, f)
        with open(HISTORY_FILE, "w") as f:
            json.dump(history_data, f)

        return jsonify({"message": "Changes saved!"})

    # Contar carritos en cada categoría
    counts = {option: 0 for option in status_options}
    for cart in carts:
        counts[cart_states[cart]["status"]] += 1

    return render_template("index.html", carts=carts, status_options=status_options,
                           cart_states=cart_states, counts=counts)

@app.route('/history')
def history():
    cart = request.args.get("cart")
    if cart in history_data:
        return jsonify({"history": history_data[cart]})
    else:
        return jsonify({"history": []})

if __name__ == "__main__":
    app.run(debug=True)
