from flask import Flask, render_template, request, jsonify
import json
import os

app = Flask(__name__)

# Lista de 40 carritos SunCart
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
os.makedirs(PERSISTENT_PATH, exist_ok=True)

# Cargar o crear archivo persistente
if os.path.exists(DATA_FILE):
    with open(DATA_FILE, "r") as f:
        cart_states = json.load(f)
else:
    cart_states = {cart: {"status": "Ready for Walk up", "comment": ""} for cart in carts}
    with open(DATA_FILE, "w") as f:
        json.dump(cart_states, f)

@app.route('/', methods=['GET', 'POST'])
def index():
    global cart_states
    if request.method == 'POST':
        for cart in carts:
            cart_states[cart]["status"] = request.form.get(f"status_{cart}")
            cart_states[cart]["comment"] = request.form.get(f"comment_{cart}")
        with open(DATA_FILE, "w") as f:
            json.dump(cart_states, f)

    # Contar carritos en cada categoría
    counts = {option: 0 for option in status_options}
    for cart in carts:
        counts[cart_states[cart]["status"]] += 1

    return render_template("index.html", carts=carts, status_options=status_options,
                           cart_states=cart_states, counts=counts)

# Endpoint para obtener los carritos de una categoría (AJAX)
@app.route('/category/<status>')
def category(status):
    result = [cart for cart in carts if cart_states[cart]["status"] == status]
    return jsonify(result)

if __name__ == "__main__":
    app.run(debug=True)
