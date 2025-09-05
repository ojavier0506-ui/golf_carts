from flask import Flask, request, jsonify, send_from_directory
import os
import json

app = Flask(__name__)

# Carpeta para guardar datos persistentes
DATA_DIR = "/data"
DATA_FILE = os.path.join(DATA_DIR, "carts.json")
os.makedirs(DATA_DIR, exist_ok=True)

# Cargar datos
def load_data():
    if not os.path.exists(DATA_FILE):
        return {"carts": []}
    with open(DATA_FILE, "r") as f:
        return json.load(f)

# Guardar datos
def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=2)

# API para obtener todos los carritos
@app.route("/api/carts", methods=["GET"])
def get_carts():
    return jsonify(load_data())

# API para agregar un carrito
@app.route("/api/carts", methods=["POST"])
def add_cart():
    data = load_data()
    cart_id = len(data["carts"]) + 1
    new_cart = {
        "name": f"SunCart {cart_id}",
        "items": []
    }
    data["carts"].append(new_cart)
    save_data(data)
    return jsonify(new_cart), 201

# API para agregar un item a un carrito
@app.route("/api/carts/<int:cart_id>/items", methods=["POST"])
def add_item(cart_id):
    data = load_data()
    if cart_id < 1 or cart_id > len(data["carts"]):
        return jsonify({"error": "Cart not found"}), 404
    item = request.json
    data["carts"][cart_id - 1]["items"].append(item)
    save_data(data)
    return jsonify(data["carts"][cart_id - 1])

# Servir HTML
@app.route("/", methods=["GET"])
def index():
    return send_from_directory("static", "index.html")

@app.route("/<path:path>")
def static_files(path):
    return send_from_directory("static", path)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
