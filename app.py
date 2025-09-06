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

# Persistencia de datos
PERSISTENT_PATH = "/persistent"
DATA_FILE = os.path.join(PERSISTENT_PATH, "data.json")
HISTORY_FILE = os.path.join(PERSISTENT_PATH, "history.json")
os.makedirs(PERSISTENT_PATH, exist_ok=True)

# Inicializar data.json
if os.path.exists(DATA_FILE):
    with open(DATA_FILE, "r") as f:
        cart_states = json.load(f)
else:
    cart_states = {cart: {"status": "Ready for Walk up", "comment": ""} for cart in carts}
    with open(DATA_FILE, "w") as f:
        json.dump(cart_states, f)

# Inicializar history.json
if os.path.exists(HISTORY_FILE):
    with open(HISTORY_FILE, "r") as f:
        history_data = json.load(f)
else:
    history_data = {}
    with open(HISTORY_FILE, "w") as f:
        json.dump(history_data, f)

@app.route('/', methods=['GET', 'POST'])
def index():
    global cart_states, history_data

    if request.method == 'POST':
        for cart in carts:
            new_status = request.form.get(f"status_{cart}")
            new_comment = request.form.get(f"comment_{cart}")
            if new_status != cart_states[cart]["status"] or new_comment != cart_states[cart]["comment"]:
                # Guardar cambios en history
                now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                history_entry = {
                    "datetime": now,
                    "status": new_status,
                    "comment": new_comment
                }
                if cart not in history_data:
                    history_data[cart] = []
                history_data[cart].append(history_entry)
                # Mantener solo los últimos 60 días
                history_data[cart] = [e for e in history_data[cart]
                                      if datetime.strptime(e["datetime"], "%Y-%m-%d %H:%M:%S") >=
                                      datetime.now() - timedelta(days=60)]

                # Actualizar estado actual
                cart_states[cart]["status"] = new_status
                cart_states[cart]["comment"] = new_comment

        # Guardar data.json y history.json
        with open(DATA_FILE, "w") as f:
            json.dump(cart_states, f)
        with open(HISTORY_FILE, "w") as f:
            json.dump(history_data, f)
        return jsonify({"message": "Changes saved successfully!"})

    # Contar carritos en cada categoría
    counts = {option: 0 for option in status_options}
    for cart in carts:
        counts[cart_states[cart]["status"]] += 1

    return render_template("index.html", carts=carts, status_options=status_options,
                           cart_states=cart_states, counts=counts)

@app.route('/history/<cart_name>')
def get_history(cart_name):
    # Retorna todos los cambios de un SunCart
    return jsonify(history_data.get(cart_name, []))

if __name__ == "__main__":
    app.run(debug=True)
