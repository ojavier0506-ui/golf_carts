from flask import Flask, render_template, request, redirect, url_for, session, send_file
from fpdf import FPDF
import sqlite3
from io import BytesIO
from datetime import datetime
import pytz

app = Flask(__name__)
app.secret_key = "supersecretkey"

DB_FILE = "database.db"

# ----------------------
# Función para DB
# ----------------------
def get_db_connection():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

# ----------------------
# Página principal
# ----------------------
@app.route("/", methods=["GET", "POST"])
def index():
    if "username" not in session:
        return redirect(url_for("login"))

    conn = get_db_connection()

    if request.method == "POST":
        cart_id = request.form["cart_id"]
        status = request.form["status"]
        comment = request.form["comment"]

        conn.execute("UPDATE carts SET status=?, comment=? WHERE id=?", (status, comment, cart_id))

        # Guardar historial
        conn.execute(
            "INSERT INTO history (cart_id, status, comment, timestamp) VALUES (?, ?, ?, ?)",
            (cart_id, status, comment, datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")),
        )

        conn.commit()

    carts = conn.execute("SELECT * FROM carts").fetchall()
    conn.close()

    return render_template("index.html", carts=carts)


# ----------------------
# Login
# ----------------------
@app.route("/login", methods=["GET", "POST"])
def login():
    error = None
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        if username == "admin" and password == "1234":
            session["username"] = username
            return redirect(url_for("index"))
        else:
            error = "Invalid credentials"
    return render_template("login.html", error=error)


@app.route("/logout")
def logout():
    session.pop("username", None)
    return redirect(url_for("login"))


# ----------------------
# Historial
# ----------------------
@app.route("/history", methods=["GET"])
def history():
    if "username" not in session:
        return redirect(url_for("login"))

    cart_id = request.args.get("cart_id")
    date_filter = request.args.get("date")

    conn = get_db_connection()
    carts = conn.execute("SELECT * FROM carts").fetchall()

    query = """
        SELECT h.id, h.timestamp, h.status, h.comment, c.name as cart_name
        FROM history h
        JOIN carts c ON h.cart_id = c.id
        WHERE 1=1
    """
    params = []

    if cart_id:
        query += " AND h.cart_id = ?"
        params.append(cart_id)

    if date_filter:
        query += " AND DATE(h.timestamp) = ?"
        params.append(date_filter)

    query += " ORDER BY h.timestamp DESC"

    history_data = conn.execute(query, params).fetchall()
    conn.close()

    return render_template("history.html", history=history_data, carts=carts)


# ----------------------
# Reporte PDF
# ----------------------
@app.route("/report", methods=["GET"])
def report():
    if "username" not in session:
        return redirect(url_for("login"))

    conn = get_db_connection()
    carts = conn.execute("SELECT * FROM carts").fetchall()
    conn.close()

    # Resumen de categorías
    category_counts = {}
    for cart in carts:
        category_counts[cart["status"]] = category_counts.get(cart["status"], 0) + 1

    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", "B", 16)
    pdf.cell(0, 10, "Reporte de SunCarts", ln=True, align="C")

    pdf.set_font("Arial", "", 12)
    pdf.cell(0, 10, "Resumen por categoría:", ln=True)
    for status, count in category_counts.items():
        pdf.cell(0, 10, f"{status}: {count} carritos", ln=True)

    pdf.ln(10)
    pdf.set_font("Arial", "B", 12)
    pdf.cell(40, 10, "Carrito")
    pdf.cell(40, 10, "Categoría")
    pdf.cell(100, 10, "Comentario", ln=True)

    pdf.set_font("Arial", "", 12)
    for cart in carts:
        pdf.cell(40, 10, cart["name"])
        pdf.cell(40, 10, cart["status"])
        pdf.multi_cell(100, 10, cart["comment"] or "")

    # Nombre del archivo con fecha (sin hora)
    cuba_tz = pytz.timezone("America/Havana")
    current_date = datetime.now(cuba_tz).strftime("%Y-%m-%d")
    filename = f"SunCarts_{current_date}.pdf"

    output = BytesIO()
    pdf.output(output, "F")
    output.seek(0)

    return send_file(output, download_name=filename, as_attachment=True)


if __name__ == "__main__":
    app.run(debug=True)
