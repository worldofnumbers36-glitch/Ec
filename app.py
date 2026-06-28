import os
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash
from flask import Flask, render_template_string, request, redirect, url_for, session, flash, abort

# Initialize Flask App
app = Flask(__name__)
app.secret_key = 'marketplay_secret_cyber_key_2026'
DATABASE = 'marketplay.db'

# Ensure directories exist
os.makedirs('uploads', exist_ok=True)

# Database Helpers
def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_db() as conn:
        conn.execute('''CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            wallet REAL DEFAULT 10000.0,
            is_admin INTEGER DEFAULT 0
        )''')
        conn.execute('''CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            price REAL NOT NULL,
            description TEXT,
            image_path TEXT,
            seller_id INTEGER,
            FOREIGN KEY(seller_id) REFERENCES users(id)
        )''')
        conn.execute('''CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_id INTEGER,
            buyer_id INTEGER,
            seller_id INTEGER,
            price REAL,
            status TEXT DEFAULT 'Pending',
            FOREIGN KEY(product_id) REFERENCES products(id),
            FOREIGN KEY(buyer_id) REFERENCES users(id),
            FOREIGN KEY(seller_id) REFERENCES users(id)
        )''')
        # Create hardcoded admin if not exists
        try:
            admin_pwd = generate_password_hash('admin123')
            conn.execute("INSERT INTO users (username, password, wallet, is_admin) VALUES ('admin', ?, 0, 1)", (admin_pwd,))
        except sqlite3.IntegrityError:
            pass
        conn.commit()

# Context Processor for global user wallet
@app.context_processor
def inject_user_wallet():
    if 'user_id' in session:
        db = get_db()
        user = db.execute("SELECT wallet, is_admin FROM users WHERE id = ?", (session['user_id'],)).fetchone()
        if user:
            return {'current_wallet': user['wallet'], 'is_admin': user['is_admin']}
    return {'current_wallet': 0, 'is_admin': 0}

# Global Styles & Base Layout HTML
BASE_CSS = """
:root {
    --bg: #0a0a16;
    --panel: rgba(20, 20, 43, 0.6);
    --border: rgba(0, 242, 254, 0.2);
    --neon-blue: #00f2fe;
    --neon-purple: #4facfe;
    --neon-pink: #ff007f;
    --text: #e0e0ff;
    --text-dim: #a0a0c0;
}
* { box-sizing: border-box; margin: 0; padding: 0; font-family: 'Segoe UI', Roboto, sans-serif; }
body { background: linear-gradient(135deg, #050510, #0a0a24, #150525); color: var(--text); min-height: 100vh; overflow-x: hidden; }
a { color: var(--neon-blue); text-decoration: none; transition: 0.3s; }
a:hover { color: var(--neon-pink); text-shadow: 0 0 10px var(--neon-pink); }
nav { background: rgba(10, 10, 30, 0.85); backdrop-filter: blur(12px); border-bottom: 1px solid var(--border); padding: 15px 40px; display: flex; justify-content: space-between; align-items: center; sticky: top; z-index: 100; }
.logo { font-size: 1.6rem; font-weight: 800; background: linear-gradient(45deg, var(--neon-blue), var(--neon-pink)); -webkit-background-clip: text; -webkit-text-fill-color: transparent; text-shadow: 0 0 20px rgba(0,242,254,0.3); }
nav .links { display: flex; gap: 25px; align-items: center; }
.container { max-width: 1200px; margin: 40px auto; padding: 0 20px; }
.glass-card { background: var(--panel); backdrop-filter: blur(16px); border: 1px solid var(--border); border-radius: 16px; padding: 30px; box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.37); margin-bottom: 30px; }
.btn { background: linear-gradient(45deg, #00f2fe, #4facfe); border: none; color: #000; padding: 12px 24px; font-weight: bold; border-radius: 8px; cursor: pointer; transition: all 0.3s ease; display: inline-block; text-align: center; text-transform: uppercase; letter-spacing: 1px; }
.btn:hover { transform: translateY(-3px); box-shadow: 0 0 15px var(--neon-blue); opacity: 0.9; }
.btn-pink { background: linear-gradient(45deg, #ff007f, #7928ca); color: #fff; }
.btn-pink:hover { box-shadow: 0 0 15px var(--neon-pink); }
.grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 30px; }
.form-group { margin-bottom: 20px; }
.form-group label { display: block; margin-bottom: 8px; color: var(--text-dim); font-size: 0.9rem; }
.form-control { width: 100%; padding: 12px; background: rgba(0,0,0,0.3); border: 1px solid var(--border); border-radius: 8px; color: #fff; outline: none; transition: 0.3s; }
.form-control:focus { border-color: var(--neon-pink); box-shadow: 0 0 10px rgba(255,0,127,0.2); }
.flash { padding: 15px; border-radius: 8px; background: rgba(255,0,127,0.2); border: 1px solid var(--neon-pink); color: #fff; margin-bottom: 20px; }
.flash.success { background: rgba(0,242,254,0.2); border-color: var(--neon-blue); }
.badge { padding: 4px 10px; border-radius: 20px; font-size: 0.8rem; font-weight: bold; text-transform: uppercase; }
.badge-pending { background: rgba(255, 165, 0, 0.2); color: orange; border: 1px solid orange; }
.badge-delivered { background: rgba(0, 255, 128, 0.2); color: #00ff80; border: 1px solid #00ff80; }
.stats-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 20px; margin-bottom: 40px; }
.stat-card { background: linear-gradient(135deg, rgba(20,20,43,0.8), rgba(10,10,25,0.8)); border: 1px solid var(--border); border-radius: 12px; padding: 20px; text-align: center; }
.stat-card h3 { font-size: 0.9rem; color: var(--text-dim); text-transform: uppercase; }
.stat-card p { font-size: 1.8rem; font-weight: bold; color: var(--neon-blue); margin-top: 10px; text-shadow: 0 0 10px rgba(0,242,254,0.3); }
table { width: 100%; border-collapse: collapse; margin-top: 20px; }
th, td { padding: 15px; text-align: left; border-bottom: 1px solid var(--border); }
th { color: var(--text-dim); text-transform: uppercase; font-size: 0.85rem; }
.prod-img { width: 100%; height: 200px; object-fit: cover; border-radius: 8px; margin-bottom: 15px; border: 1px solid rgba(255,255,255,0.1); }
"""

LAYOUT_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>MarketPlay - Cyber Marketplace</title>
    <style>""" + BASE_CSS + """</style>
</head>
<body>
    <nav>
        <a href="/" class="logo">MARKETPLAY</a>
        <div class="links">
            <a href="/">Market</a>
            {% if session.get('user_id') %}
                <a href="/game">Game Zone</a>
                <a href="/dashboard">Dashboard</a>
                {% if is_admin %}<a href="/admin" style="color:var(--neon-pink);">Admin</a>{% endif %}
                <span style="color:var(--neon-blue); font-weight:bold;">₹{{ "{:,.2f}".format(current_wallet) }}</span>
                <a href="/logout" class="btn btn-pink" style="padding: 6px 15px; font-size:0.85rem;">Logout</a>
            {% else %}
                <a href="/login">Login</a>
                <a href="/register" class="btn" style="padding: 6px 15px; font-size:0.85rem;">Join</a>
            {% endif %}
        </div>
    </nav>
    <div class="container">
        {% with messages = get_flashed_messages(with_categories=true) %}
            {% if messages %}
                {% for cat, msg in messages %}
                    <div class="flash {{ cat }}">{{ msg }}</div>
                {% endfor %}
            {% endif %}
        {% endwith %}
        {% block content %}{% endblock %}
    </div>
</body>
</html>
"""

# Routes
@app.route('/')
def index():
    q = request.args.get('q', '')
    db = get_db()
    if q:
        prods = db.execute("SELECT p.*, u.username FROM products p JOIN users u ON p.seller_id = u.id WHERE p.name LIKE ? OR p.description LIKE ?", (f'%{q}%', f'%{q}%')).fetchall()
    else:
        prods = db.execute("SELECT p.*, u.username FROM products p JOIN users u ON p.seller_id = u.id").fetchall()
    
    html = """
    {% extends "layout" %}
    {% block content %}
    <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:30px;">
        <h1 style="text-shadow: 0 0 10px var(--neon-blue);">Cyber Matrix Market</h1>
        <form action="/" method="get" style="display:flex; gap:10px; width:400px;">
            <input type="text" name="q" placeholder="Search tech artifacts..." class="form-control" value="{{ q }}">
            <button type="submit" class="btn">Search</button>
        </form>
    </div>
    <div class="grid">
        {% for p in prods %}
        <div class="glass-card" style="margin-bottom:0; display:flex; flex-direction:column; justify-content:between;">
            {% if p.image_path %}
                <img src="/{{ p.image_path }}" class="prod-img">
            {% else %}
                <div class="prod-img" style="background:rgba(0,0,0,0.4); display:flex; align-items:center; justify-content:center; color:var(--text-dim);">No Uplink Image</div>
            {% endif %}
            <h3>{{ p.name }}</h3>
            <p style="color:var(--text-dim); font-size:0.9rem; margin:10px 0; flex-grow:1;">{{ p.description }}</p>
            <div style="display:flex; justify-content:space-between; align-items:center; margin-top:15px;">
                <span style="color:var(--neon-blue); font-size:1.3rem; font-weight:bold;">₹{{ p.price }}</span>
                <span style="font-size:0.8rem; color:var(--text-dim);">Seller: {{ p.username }}</span>
            </div>
            {% if session.get('user_id') and p.seller_id != session['user_id'] %}
                <a href="/buy/{{ p.id }}" class="btn" style="margin-top:15px; width:100%;">Acquire Item</a>
            {% elif session.get('user_id') and p.seller_id == session['user_id'] %}
                <button class="btn btn-pink" style="margin-top:15px; width:100%; cursor:not-allowed;" disabled>Your Item</button>
            {% else %}
                <a href="/login" class="btn" style="margin-top:15px; width:100%;">Login to Acquire</a>
            {% endif %}
        </div>
        {% endfor %}
    </div>
    {% endblock %}
    """
    return render_template_string(html, prods=prods, q=q)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username'].strip()
        password = request.form['password']
        if not username or not password:
            flash('All coordinates required.', 'error')
            return redirect(url_for('register'))
        db = get_db()
        try:
            db.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, generate_password_hash(password)))
            db.commit()
            flash('Access granted. Account initialization bonus of ₹10,000 credited.', 'success')
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            flash('Identity designation already occupied.', 'error')
    
    return render_template_string("""
    {% extends "layout" %}
    {% block content %}
    <div class="glass-card" style="max-width:450px; margin: 60px auto;">
        <h2 style="margin-bottom:20px; text-shadow: 0 0 10px var(--neon-blue);">Initialize Persona</h2>
        <form method="post">
            <div class="form-group">
                <label>Username</label>
                <input type="text" name="username" class="form-control" required autocomplete="off">
            </div>
            <div class="form-group">
                <label>Password Matrix</label>
                <input type="password" name="password" class="form-control" required>
            </div>
            <button type="submit" class="btn style="width:100%;">Create Account</button>
        </form>
    </div>
    {% endblock %}
    """)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username'].strip()
        password = request.form['password']
        db = get_db()
        user = db.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
        if user and check_password_hash(user['password'], password):
            session['user_id'] = user['id']
            session['username'] = user['username']
            flash(f'Identity Verified. Welcome back, {username}.', 'success')
            return redirect(url_for('dashboard'))
        flash('Invalid security credentials.', 'error')
    
    return render_template_string("""
    {% extends "layout" %}
    {% block content %}
    <div class="glass-card" style="max-width:450px; margin: 60px auto;">
        <h2 style="margin-bottom:20px; text-shadow: 0 0 10px var(--neon-pink);">Establish Link</h2>
        <form method="post">
            <div class="form-group">
                <label>Username</label>
                <input type="text" name="username" class="form-control" required autocomplete="off">
            </div>
            <div class="form-group">
                <label>Security Code</label>
                <input type="password" name="password" class="form-control" required>
            </div>
            <button type="submit" class="btn btn-pink" style="width:100%;">Authenticate</button>
        </form>
    </div>
    {% endblock %}
    """)

@app.route('/logout')
def logout():
    session.clear()
    flash('Link terminated cleanly.', 'success')
    return redirect(url_for('index'))

@app.route('/dashboard', methods=['GET', 'POST'])
def dashboard():
    if 'user_id' not in session: return redirect(url_for('login'))
    uid = session['user_id']
    db = get_db()
    
    if request.method == 'POST':
        name = request.form['name'].strip()
        price = float(request.form['price'])
        desc = request.form['description'].strip()
        file = request.files.get('image')
        
        img_path = None
        if file and file.filename:
            img_path = os.path.join('uploads', f"{uid}_{file.filename}")
            file.save(img_path)
            
        db.execute("INSERT INTO products (name, price, description, image_path, seller_id) VALUES (?, ?, ?, ?, ?)",
                   (name, price, desc, img_path, uid))
        db.commit()
        flash('Artifact uploaded to network matrix.', 'success')
        return redirect(url_for('dashboard'))

    user = db.execute("SELECT * FROM users WHERE id = ?", (uid,)).fetchone()
    my_prods = db.execute("SELECT * FROM products WHERE seller_id = ?", (uid,)).fetchall()
    
    # Orders bought by user
    my_orders = db.execute("""
        SELECT o.*, p.name as prod_name, u.username as seller_name 
        FROM orders o 
        JOIN products p ON o.product_id = p.id 
        JOIN users u ON o.seller_id = u.id 
        WHERE o.buyer_id = ?
    """, (uid,)).fetchall()
    
    # Earnings from completed sales
    sales = db.execute("SELECT SUM(price) as total FROM orders WHERE seller_id = ? AND status = 'Delivered'", (uid,)).fetchone()
    earnings = sales['total'] if sales['total'] else 0.0

    return render_template_string("""
    {% extends "layout" %}
    {% block content %}
    <h1 style="margin-bottom:30px;">Neural Deck: {{ user.username }}</h1>
    
    <div class="stats-grid">
        <div class="stat-card"><h3>Wallet Core</h3><p>₹{{ "{:,.2f}".format(user.wallet) }}</p></div>
        <div class="stat-card"><h3>Active Offerings</h3><p>{{ my_prods|length }}</p></div>
        <div class="stat-card"><h3>Acquisitions</h3><p>{{ my_orders|length }}</p></div>
        <div class="stat-card"><h3>Total Earnings</h3><p style="color:var(--neon-pink);">RGB ₹{{ "{:,.2f}".format(earnings) }}</p></div>
    </div>

    <div style="display:grid; grid-template-columns: 2fr 1fr; gap:30px;">
        <div>
            <div class="glass-card">
                <h2>Your Acquisitions Track</h2>
                {% if my_orders %}
                <table>
                    <thead>
                        <tr><th>Item</th><th>Vendor</th><th>Price</th><th>Status</th><th>Protocol</th></tr>
                    </thead>
                    <tbody>
                        {% for o in my_orders %}
                        <tr>
                            <td>{{ o.prod_name }}</td>
                            <td>{{ o.seller_name }}</td>
                            <td>₹{{ o.price }}</td>
                            <td><span class="badge badge-{{ o.status|lower }}">{{ o.status }}</span></td>
                            <td>
                                {% if o.status == 'Pending' %}
                                    <a href="/order/deliver/{{ o.id }}" class="btn" style="padding:4px 10px; font-size:0.75rem;">Confirm Delivery</a>
                                {% else %}
                                    <span style="color:var(--text-dim); font-size:0.8rem;">Completed</span>
                                {% endif %}
                            </td>
                        </tr>
                        {% endfor %}
                    </tbody>
                </table>
                {% else %}<p style="margin-top:15px; color:var(--text-dim);">No transactions logged.</p>{% endif %}
            </div>

            <div class="glass-card">
                <h2>Your Marketplace Offerings</h2>
                {% if my_prods %}
                <table>
                    <thead><tr><th>Designation</th><th>Price Matrix</th></tr></thead>
                    <tbody>
                        {% for p in my_prods %}
                        <tr><td>{{ p.name }}</td><td>₹{{ p.price }}</td></tr>
                        {% endfor %}
                    </tbody>
                </table>
                {% else %}<p style="margin-top:15px; color:var(--text-dim);">No network data available.</p>{% endif %}
            </div>
        </div>

        <div>
            <div class="glass-card">
                <h2>Forge New Listing</h2>
                <form method="post" enctype="multipart/form-data" style="margin-top:20px;">
                    <div class="form-group"><label>Product Name</label><input type="text" name="name" class="form-control" required></div>
                    <div class="form-group"><label>Price (₹)</label><input type="number" step="0.01" name="price" class="form-control" required></div>
                    <div class="form-group"><label>Data Specifications</label><textarea name="description" class="form-control" rows="3" required></textarea></div>
                    <div class="form-group"><label>Visual Blueprint (Optional)</label><input type="file" name="image" class="form-control" style="padding:8px;"></div>
                    <button type="submit" class="btn btn-pink" style="width:100%; margin-top:10px;">Transmit Data</button>
                </form>
            </div>
        </div>
    </div>
    {% endblock %}
    """, user=user, my_prods=my_prods, my_orders=my_orders, earnings=earnings)

@app.route('/buy/<int:product_id>')
def buy_product(product_id):
    if 'user_id' not in session: return redirect(url_for('login'))
    uid = session['user_id']
    db = get_db()
    
    prod = db.execute("SELECT * FROM products WHERE id = ?", (product_id,)).fetchone()
    buyer = db.execute("SELECT wallet FROM users WHERE id = ?", (uid,)).fetchone()
    
    if not prod: abort(404)
    if prod['seller_id'] == uid:
        flash("Cannot acquire your own technology architecture.", 'error')
        return redirect(url_for('index'))
        
    if buyer['wallet'] < prod['price']:
        flash("Insufficient funds in net wallet core.", 'error')
        return redirect(url_for('index'))
        
    # Deduct funds upfront and log escrow order
    db.execute("UPDATE users SET wallet = wallet - ? WHERE id = ?", (prod['price'], uid))
    db.execute("INSERT INTO orders (product_id, buyer_id, seller_id, p
