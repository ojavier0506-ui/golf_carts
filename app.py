from flask import Flask, render_template, request
import json
import os

app = Flask(__name__)

# Define cart list
carts = [f"Cart {i+1}" for i in range(40)]

# Define status options
status_options = [
    "Charging",
    "Ready for Walk up",
    "Being used by Guest",
    "Out of Service",
    "Other"
]

# Path del archivo JSON donde se guardan los datos
DATA_FILE = 'data.json'

# Cargar estados desde JSON si existe
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

        # Guardar cambios en JSON
        with open(DATA_FILE, 'w') as f:
            json.dump(cart_states, f)

    # Contar carritos en cada categoría
    counts = {option: 0 for option in status_options}
    for cart in carts:
        counts[cart_states[cart]["status"]] += 1

    return render_template('index.html', carts=carts, status_options=status_options,
                           cart_states=cart_states, counts=counts)

if __name__ == "__main__":
    app.run(debug=True)
