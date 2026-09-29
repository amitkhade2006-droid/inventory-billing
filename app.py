from flask import Flask, render_template, request, redirect
import sqlite3
from datetime import datetime

app = Flask(__name__)


def create_database():
    conn = sqlite3.connect("shop.db")

    conn.execute("""
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            category TEXT,
            price REAL NOT NULL,
            quantity INTEGER NOT NULL
        )
    """)
    conn.execute("""
    CREATE TABLE IF NOT EXISTS customers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        mobile TEXT NOT NULL,
        address TEXT
    )
 """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS bills (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_name TEXT NOT NULL,
            product_name TEXT NOT NULL,
            quantity INTEGER NOT NULL,
            total REAL NOT NULL
        )
    """)
    # Add bill date column
    try:
        conn.execute(
            "ALTER TABLE bills ADD COLUMN bill_date TEXT"
        )
    except sqlite3.OperationalError:
        pass
    conn.execute("""
        CREATE TABLE IF NOT EXISTS bill_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            bill_id INTEGER NOT NULL,
            product_name TEXT NOT NULL,
            price REAL NOT NULL,
            quantity INTEGER NOT NULL,
            total REAL NOT NULL
        )
    """)

    conn.commit()
    conn.close()


create_database()


@app.route("/")
def home():
    return render_template("index.html")

@app.route("/dashboard")
def dashboard():

    conn = sqlite3.connect("shop.db")
    conn.row_factory = sqlite3.Row

    # Total Products
    total_products = conn.execute(
        "SELECT COUNT(*) FROM products"
    ).fetchone()[0]

    # Total Customers
    total_customers = conn.execute(
        "SELECT COUNT(*) FROM customers"
    ).fetchone()[0]

    # Total Bills
    total_bills = conn.execute(
        "SELECT COUNT(*) FROM bills"
    ).fetchone()[0]

    # Total Sales
    total_sales = conn.execute(
        "SELECT SUM(total) FROM bills"
    ).fetchone()[0]

    if total_sales is None:
        total_sales = 0

    # Low Stock Products
    low_stock_products = conn.execute(
        "SELECT * FROM products WHERE quantity <= 5 ORDER BY quantity ASC"
    ).fetchall()

    # Product Sales Summary
    product_sales = conn.execute("""
        SELECT product_name, SUM(total) AS sales
        FROM bills
        GROUP BY product_name
        ORDER BY sales DESC
    """).fetchall()

    # Recent Bills
    recent_bills = conn.execute(
        "SELECT * FROM bills ORDER BY id DESC LIMIT 5"
    ).fetchall()

    # Low Stock Count
    low_stock = len(low_stock_products)

    conn.close()

    return render_template(
        "dashboard.html",
        total_products=total_products,
        total_customers=total_customers,
        total_bills=total_bills,
        total_sales=total_sales,
        low_stock=low_stock,
        low_stock_products=low_stock_products,
        recent_bills=recent_bills,
        product_sales=product_sales
    )


@app.route("/products", methods=["GET", "POST"])
def products():

    if request.method == "POST":

        name = request.form["name"]
        category = request.form["category"]
        price = request.form["price"]
        quantity = request.form["quantity"]

        conn = sqlite3.connect("shop.db")

        conn.execute(
            "INSERT INTO products (name, category, price, quantity) VALUES (?, ?, ?, ?)",
            (name, category, price, quantity)
        )

        conn.commit()
        conn.close()

        return redirect("/products")

    conn = sqlite3.connect("shop.db")
    conn.row_factory = sqlite3.Row

    products = conn.execute("SELECT * FROM products").fetchall()

    conn.close()

    return render_template("products.html", products=products)

@app.route("/edit/<int:id>", methods=["GET", "POST"])
def edit_product(id):

    conn = sqlite3.connect("shop.db")
    conn.row_factory = sqlite3.Row

    if request.method == "POST":

        name = request.form["name"]
        category = request.form["category"]
        price = request.form["price"]
        quantity = request.form["quantity"]

        conn.execute(
            "UPDATE products SET name=?, category=?, price=?, quantity=? WHERE id=?",
            (name, category, price, quantity, id)
        )

        conn.commit()
        conn.close()

        return redirect("/products")

    product = conn.execute(
        "SELECT * FROM products WHERE id=?",
        (id,)
    ).fetchone()

    conn.close()

    return render_template("edit.html", product=product)

@app.route("/customers", methods=["GET", "POST"])
def customers():

    if request.method == "POST":
        name = request.form["name"]
        mobile = request.form["mobile"]
        address = request.form["address"]

        conn = sqlite3.connect("shop.db")

        conn.execute(
            "INSERT INTO customers (name, mobile, address) VALUES (?, ?, ?)",
            (name, mobile, address)
        )

        conn.commit()
        conn.close()

        return redirect("/customers")

    conn = sqlite3.connect("shop.db")
    conn.row_factory = sqlite3.Row

    customers = conn.execute(
        "SELECT * FROM customers"
    ).fetchall()

    conn.close()

    return render_template("customers.html", customers=customers) 

@app.route("/delete_customer/<int:id>")
def delete_customer(id):

    conn = sqlite3.connect("shop.db")

    conn.execute(
        "DELETE FROM customers WHERE id=?",
        (id,)
    )

    conn.commit()
    conn.close()

    return redirect("/customers")

@app.route("/edit_customer/<int:id>", methods=["GET", "POST"])
def edit_customer(id):

    conn = sqlite3.connect("shop.db")
    conn.row_factory = sqlite3.Row

    customer = conn.execute(
        "SELECT * FROM customers WHERE id=?",
        (id,)
    ).fetchone()

    if request.method == "POST":

        name = request.form["name"]
        mobile = request.form["mobile"]
        address = request.form["address"]

        conn.execute(
            "UPDATE customers SET name=?, mobile=?, address=? WHERE id=?",
            (name, mobile, address, id)
        )

        conn.commit()
        conn.close()

        return redirect("/customers")

    conn.close()

    return render_template("edit_customer.html", customer=customer)


@app.route("/billing", methods=["GET", "POST"])
def billing():

    conn = sqlite3.connect("shop.db")
    conn.row_factory = sqlite3.Row

    if request.method == "POST":

        import json

        customer_id = request.form.get("customer_id")
        bill_items_data = request.form.get("bill_items")

        if not customer_id:
            conn.close()
            return "Please select a customer"

        if not bill_items_data:
            conn.close()
            return "No products added to bill"

        bill_items = json.loads(bill_items_data)

        customer = conn.execute(
            "SELECT * FROM customers WHERE id=?",
            (customer_id,)
        ).fetchone()

        if not customer:
            conn.close()
            return "Customer not found"

        grand_total = 0
        total_quantity = 0

        # Check stock and calculate total
        for item in bill_items:

            product = conn.execute(
                "SELECT * FROM products WHERE id=?",
                (item["productId"],)
            ).fetchone()

            if not product:
                conn.close()
                return "Product not found"

            quantity = int(item["quantity"])

            if quantity > product["quantity"]:
                conn.close()
                return (
                    "Not enough stock for "
                    + product["name"]
                )

            grand_total += product["price"] * quantity
            total_quantity += quantity

        # Create bill date and time
        bill_date = datetime.now().strftime(
            "%d/%m/%Y %I:%M %p"
        )

        # Create main bill record
        cursor = conn.execute(
            """
            INSERT INTO bills
            (customer_name, product_name, quantity, total, bill_date)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                customer["name"],
                "Multiple Products",
                total_quantity,
                grand_total,
                bill_date
            )
        )

        bill_id = cursor.lastrowid

        # Save every product in bill_items
        for item in bill_items:

            product = conn.execute(
                "SELECT * FROM products WHERE id=?",
                (item["productId"],)
            ).fetchone()

            quantity = int(item["quantity"])

            item_total = product["price"] * quantity

            conn.execute(
                """
                INSERT INTO bill_items
                (bill_id, product_name, price, quantity, total)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    bill_id,
                    product["name"],
                    product["price"],
                    quantity,
                    item_total
                )
            )

            # Reduce product stock
            new_quantity = product["quantity"] - quantity

            conn.execute(
                """
                UPDATE products
                SET quantity=?
                WHERE id=?
                """,
                (
                    new_quantity,
                    product["id"]
                )
            )

        conn.commit()

        # Get saved bill items
        saved_items = conn.execute(
            """
            SELECT *
            FROM bill_items
            WHERE bill_id=?
            """,
            (bill_id,)
        ).fetchall()

        conn.close()

        return render_template(
            "bill.html",
            customer_name=customer["name"],
            items=saved_items,
            total=grand_total,
            bill_id=bill_id,
            bill_date=bill_date
        )

    # GET request

    products = conn.execute(
        """
        SELECT *
        FROM products
        WHERE quantity > 0
        """
    ).fetchall()

    customers = conn.execute(
        """
        SELECT *
        FROM customers
        """
    ).fetchall()

    conn.close()

    return render_template(
        "billing.html",
        products=products,
        customers=customers
    )
@app.route("/bill_history")
def bill_history():

    conn = sqlite3.connect("shop.db")
    conn.row_factory = sqlite3.Row

    bills = conn.execute(
        "SELECT * FROM bills ORDER BY id DESC"
    ).fetchall()

    conn.close()

    return render_template(
        "bill_history.html",
        bills=bills
    )
@app.route("/bill/<int:bill_id>")
def view_bill(bill_id):

    conn = sqlite3.connect("shop.db")
    conn.row_factory = sqlite3.Row

    bill = conn.execute(
        "SELECT * FROM bills WHERE id=?",
        (bill_id,)
    ).fetchone()

    if not bill:
        conn.close()
        return "Bill not found"

    items = conn.execute(
        """
        SELECT *
        FROM bill_items
        WHERE bill_id=?
        """,
        (bill_id,)
    ).fetchall()

    conn.close()

    return render_template(
    "bill.html",
    customer_name=bill["customer_name"],
    items=items,
    total=bill["total"],
    bill_id=bill["id"],
    bill_date=bill["bill_date"]
 )

@app.route("/delete/<int:id>")
def delete_product(id):
    conn = sqlite3.connect("shop.db")

    conn.execute(
        "DELETE FROM products WHERE id = ?",
        (id,)
    )

    conn.commit()
    conn.close()

    return redirect("/products")


if __name__ == "__main__":
    app.run(debug=True)