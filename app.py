from flask import Flask, render_template, request, redirect, url_for, session, flash
import sqlite3, os
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "change-this-secret-key-for-demo")
DB = os.path.join(os.path.dirname(__file__), "freshmart.db")

def connect():
    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    return con

def init_db():
    with connect() as con:
        con.executescript("""
        CREATE TABLE IF NOT EXISTS users(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            is_admin INTEGER NOT NULL DEFAULT 0
        );
        CREATE TABLE IF NOT EXISTS products(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            category TEXT NOT NULL,
            price REAL NOT NULL,
            unit TEXT NOT NULL,
            emoji TEXT NOT NULL,
            stock INTEGER NOT NULL DEFAULT 50
        );
        CREATE TABLE IF NOT EXISTS orders(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            customer_name TEXT NOT NULL,
            address TEXT NOT NULL,
            total REAL NOT NULL,
            status TEXT NOT NULL DEFAULT 'Placed',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS order_items(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id INTEGER NOT NULL,
            product_name TEXT NOT NULL,
            quantity INTEGER NOT NULL,
            price REAL NOT NULL
        );
        """)
        count = con.execute("SELECT COUNT(*) FROM products").fetchone()[0]
        if count == 0:
            products = [
                ("Tomato","Vegetables",35,"kg","🍅",60),
                ("Potato","Vegetables",30,"kg","🥔",70),
                ("Carrot","Vegetables",45,"kg","🥕",40),
                ("Apple","Fruits",120,"kg","🍎",30),
                ("Banana","Fruits",50,"dozen","🍌",35),
                ("Orange","Fruits",80,"kg","🍊",40),
                ("Milk","Dairy",28,"500 ml","🥛",50),
                ("Bread","Bakery",40,"pack","🍞",25),
                ("Rice","Grains",65,"kg","🍚",100),
                ("Eggs","Dairy",72,"12 pcs","🥚",40),
                ("Onion","Vegetables",40,"kg","🧅",55),
                ("Spinach","Vegetables",25,"bunch","🥬",30)
            ]
            con.executemany("INSERT INTO products(name,category,price,unit,emoji,stock) VALUES(?,?,?,?,?,?)", products)
        # Demo admin: admin@freshmart.com / admin123
        admin = con.execute("SELECT id FROM users WHERE email=?", ("admin@freshmart.com",)).fetchone()
        if not admin:
            con.execute("INSERT INTO users(name,email,password,is_admin) VALUES(?,?,?,1)",
                        ("FreshMart Admin","admin@freshmart.com",generate_password_hash("admin123")))

def current_user():
    if "user_id" not in session:
        return None
    with connect() as con:
        return con.execute("SELECT id,name,email,is_admin FROM users WHERE id=?",
                           (session["user_id"],)).fetchone()

@app.context_processor
def common():
    cart = session.get("cart", {})
    return {"cart_count": sum(int(q) for q in cart.values()), "user": current_user()}

@app.route("/")
def index():
    search = request.args.get("q","").strip()
    category = request.args.get("category","")
    with connect() as con:
        sql = "SELECT * FROM products WHERE stock > 0"
        params = []
        if search:
            sql += " AND name LIKE ?"
            params.append("%"+search+"%")
        if category:
            sql += " AND category=?"
            params.append(category)
        products = con.execute(sql+" ORDER BY category,name",params).fetchall()
        categories = con.execute("SELECT DISTINCT category FROM products ORDER BY category").fetchall()
    return render_template("index.html", products=products, categories=categories, q=search, selected=category)

@app.route("/register", methods=["GET","POST"])
def register():
    if request.method == "POST":
        name = request.form.get("name","").strip()
        email = request.form.get("email","").strip().lower()
        password = request.form.get("password","")
        if not name or not email or len(password) < 6:
            flash("Enter all details. Password must contain at least 6 characters.")
            return render_template("register.html")
        try:
            with connect() as con:
                con.execute("INSERT INTO users(name,email,password) VALUES(?,?,?)",
                            (name,email,generate_password_hash(password)))
            flash("Account created! Please log in.")
            return redirect(url_for("login"))
        except sqlite3.IntegrityError:
            flash("This email is already registered.")
    return render_template("register.html")

@app.route("/login", methods=["GET","POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email","").strip().lower()
        password = request.form.get("password","")
        with connect() as con:
            account = con.execute("SELECT * FROM users WHERE email=?", (email,)).fetchone()
        if account and check_password_hash(account["password"],password):
            session.clear()
            session["user_id"] = account["id"]
            session["cart"] = {}
            flash("Welcome to FreshMart!")
            return redirect(url_for("index"))
        flash("Invalid email or password.")
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    flash("You have logged out.")
    return redirect(url_for("index"))

@app.route("/add/<int:product_id>", methods=["POST"])
def add_to_cart(product_id):
    if not current_user():
        flash("Please log in before adding items.")
        return redirect(url_for("login"))
    with connect() as con:
        product = con.execute("SELECT id,stock FROM products WHERE id=?", (product_id,)).fetchone()
    if not product or product["stock"] < 1:
        flash("Product is unavailable.")
        return redirect(url_for("index"))
    cart = session.setdefault("cart", {})
    cart[str(product_id)] = min(int(cart.get(str(product_id),0))+1, product["stock"])
    session["cart"] = cart
    flash("Added to cart.")
    return redirect(request.referrer or url_for("index"))

@app.route("/cart")
def cart():
    cart_data = session.get("cart", {})
    items, total = [], 0
    if cart_data:
        ids = [int(pid) for pid in cart_data]
        placeholders = ",".join("?" for _ in ids)
        with connect() as con:
            products = con.execute(f"SELECT * FROM products WHERE id IN ({placeholders})",ids).fetchall()
        for p in products:
            qty = min(int(cart_data.get(str(p["id"]),1)), p["stock"])
            subtotal = p["price"] * qty
            total += subtotal
            items.append({"product":p,"qty":qty,"subtotal":subtotal})
    return render_template("cart.html", items=items, total=total)

@app.route("/cart/update/<int:product_id>", methods=["POST"])
def update_cart(product_id):
    qty = int(request.form.get("quantity",1))
    cart = session.get("cart", {})
    if qty <= 0:
        cart.pop(str(product_id),None)
    else:
        with connect() as con:
            p = con.execute("SELECT stock FROM products WHERE id=?", (product_id,)).fetchone()
        if p:
            cart[str(product_id)] = min(qty,p["stock"])
    session["cart"] = cart
    return redirect(url_for("cart"))

@app.route("/checkout", methods=["GET","POST"])
def checkout():
    if not current_user():
        return redirect(url_for("login"))
    cart_data = session.get("cart", {})
    if not cart_data:
        flash("Your cart is empty.")
        return redirect(url_for("cart"))
    with connect() as con:
        ids = [int(pid) for pid in cart_data]
        placeholders = ",".join("?" for _ in ids)
        products = con.execute(f"SELECT * FROM products WHERE id IN ({placeholders})",ids).fetchall()
    items, total = [], 0
    for p in products:
        qty = min(int(cart_data.get(str(p["id"]),1)),p["stock"])
        if qty > 0:
            subtotal = p["price"]*qty
            total += subtotal
            items.append((p,qty,subtotal))
    if request.method == "POST":
        address = request.form.get("address","").strip()
        customer_name = request.form.get("customer_name","").strip()
        if not address or not customer_name:
            flash("Please enter your name and delivery address.")
            return render_template("checkout.html",items=items,total=total)
        with connect() as con:
            cur = con.execute("INSERT INTO orders(user_id,customer_name,address,total) VALUES(?,?,?,?)",
                              (session["user_id"],customer_name,address,total))
            order_id = cur.lastrowid
            for p,qty,subtotal in items:
                con.execute("INSERT INTO order_items(order_id,product_name,quantity,price) VALUES(?,?,?,?)",
                            (order_id,p["name"],qty,p["price"]))
                con.execute("UPDATE products SET stock=MAX(0,stock-?) WHERE id=?",(qty,p["id"]))
        session["cart"] = {}
        flash(f"Order #{order_id} placed successfully!")
        return redirect(url_for("orders"))
    return render_template("checkout.html",items=items,total=total)

@app.route("/orders")
def orders():
    u = current_user()
    if not u:
        return redirect(url_for("login"))
    with connect() as con:
        rows = con.execute("SELECT * FROM orders WHERE user_id=? ORDER BY id DESC",(u["id"],)).fetchall()
    return render_template("orders.html",orders=rows)

@app.route("/admin", methods=["GET","POST"])
def admin():
    u = current_user()
    if not u or not u["is_admin"]:
        flash("Admin login required.")
        return redirect(url_for("login"))
    if request.method == "POST":
        name = request.form.get("name","").strip()
        category = request.form.get("category","").strip()
        unit = request.form.get("unit","").strip()
        emoji = request.form.get("emoji","🛒").strip() or "🛒"
        try:
            price = float(request.form.get("price",0))
            stock = int(request.form.get("stock",0))
            if name and category and unit and price > 0 and stock >= 0:
                with connect() as con:
                    con.execute("INSERT INTO products(name,category,price,unit,emoji,stock) VALUES(?,?,?,?,?,?)",
                                (name,category,price,unit,emoji,stock))
                flash("Product added.")
            else:
                flash("Please enter valid product details.")
        except ValueError:
            flash("Price and stock must be numbers.")
    with connect() as con:
        products = con.execute("SELECT * FROM products ORDER BY id DESC").fetchall()
        orders = con.execute("SELECT * FROM orders ORDER BY id DESC").fetchall()
    return render_template("admin.html",products=products,orders=orders)

@app.route("/admin/delete/<int:product_id>", methods=["POST"])
def delete_product(product_id):
    u = current_user()
    if not u or not u["is_admin"]:
        return redirect(url_for("login"))
    with connect() as con:
        con.execute("DELETE FROM products WHERE id=?",(product_id,))
    flash("Product deleted.")
    return redirect(url_for("admin"))

if __name__ == "__main__":
    init_db()
    app.run(debug=True)
