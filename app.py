from flask import Flask, render_template, request
import json
import os

app = Flask(__name__)

carts = [f"Cart {i+1}" for i in range(40)]
status_options = ["Charging", "Ready for Walk up", "Being used by Guest", "Out of Service", "Other"]

# Ruta del archivo JSON en carpeta persistente
PERSISTENT_PATH = '/persistent/data'
DATA_FILE = os.path.join(PERSISTENT_PATH, 'data.json')

# Asegurarse de que la carpeta exista
os.makedirs(PERSISTENT_PATH, exist_ok=True)

# Cargar datos si existe
if os.path.exists(DATA_FILE):
    with open(DATA_FILE, 'r') as f:
        cart_states = json.load(f)
else:
    cart_states = {cart: {"status": "Ready for Walk up", "comment": ""} for cart in carts}

@app.route('/', methods=['GET', 'POST'])
def index():
    global cart_states

    if request.method == 'POST':
        for cart in carts:
            cart_states[cart]["status"] = request.form.get(f"status_{cart}")
            cart_states[cart]["comment"] = request.form.get(f"comment_{cart}")

        # Guardar cambios en JSON persistente
        with open(DATA_FILE, 'w') as f:
            json.dump(cart_states, f)

    counts = {option: 0 for option in status_options}
    for cart in carts:
        counts[cart_states[cart]["status"]] += 1

    return render_template('index.html', carts=carts, status_options=status_options,
                           cart_states=cart_states, counts=counts)

if __name__ == "__main__":
    app.run(debug=True)
