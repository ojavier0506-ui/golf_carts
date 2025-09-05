from flask import Flask, render_template, request


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


# Store cart states
cart_states = {cart: {"status": "Ready for Walk up", "comment": ""} for cart in carts}


@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        for cart in carts:
            cart_states[cart]["status"] = request.form.get(f"status_{cart}")
            cart_states[cart]["comment"] = request.form.get(f"comment_{cart}")


    # Count carts in each category
    counts = {option: 0 for option in status_options}
    for cart in carts:
        counts[cart_states[cart]["status"]] += 1


    return render_template('index.html', carts=carts, status_options=status_options,
                            cart_states=cart_states, counts=counts)


if __name__ == "__main__":
    app.run(debug=True)