from flask import Flask, request, jsonify, render_template, redirect, url_for, session
from datetime import datetime, timedelta
import sqlite3
import secrets
import hashlib

app = Flask(__name__)
app.secret_key = "your_secret_key_here" 


def init_db():
    conn = sqlite3.connect('licenses.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS licenses
                 (license_key TEXT PRIMARY KEY, expiry_date TEXT, active INTEGER, buyer_name TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS users
                 (username TEXT PRIMARY KEY, password TEXT)''')

    hashed_password = hashlib.sha256("KMA123".encode()).hexdigest()
    c.execute("INSERT OR IGNORE INTO users (username, password) VALUES (?, ?)", 
              ('amirkma', hashed_password))
    conn.commit()
    conn.close()


def generate_license_key():
    return secrets.token_hex(16)


def is_license_valid(expiry_date):
    return datetime.strptime(expiry_date, '%Y-%m-%d') >= datetime.now()


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        hashed_password = hashlib.sha256(password.encode()).hexdigest()
        
        conn = sqlite3.connect('licenses.db')
        c = conn.cursor()
        c.execute("SELECT * FROM users WHERE username = ? AND password = ?", 
                  (username, hashed_password))
        user = c.fetchone()
        conn.close()
        
        if user:
            session['logged_in'] = True
            return redirect(url_for('dashboard'))
    return render_template('login.html', error="Password or Username It is wrong !")
    return render_template('login.html')


@app.route('/dashboard', methods=['GET', 'POST'])
def dashboard():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
        
    conn = sqlite3.connect('licenses.db')
    c = conn.cursor()
    
    if request.method == 'POST':
        if 'generate' in request.form:
            license_key = generate_license_key()
            expiry_days = int(request.form['expiry_days'])
            expiry_date = (datetime.now() + timedelta(days=expiry_days)).strftime('%Y-%m-%d')
            buyer_name = request.form.get('buyer_name', 'Unknown')  # نام خریدار، پیش‌فرض Unknown
            c.execute("INSERT INTO licenses (license_key, expiry_date, active, buyer_name) VALUES (?, ?, ?, ?)",
                      (license_key, expiry_date, 1, buyer_name))
            conn.commit()
        elif 'delete' in request.form:
            license_key = request.form['license_key']
            c.execute("DELETE FROM licenses WHERE license_key = ?", (license_key,))
            conn.commit()
        elif 'toggle_active' in request.form:
            license_key = request.form['license_key']
            c.execute("SELECT active FROM licenses WHERE license_key = ?", (license_key,))
            current_status = c.fetchone()[0]
            new_status = 0 if current_status else 1
            c.execute("UPDATE licenses SET active = ? WHERE license_key = ?", (new_status, license_key))
            conn.commit()
    
    c.execute("SELECT license_key, expiry_date, active, buyer_name FROM licenses")
    licenses = c.fetchall()
    conn.close()
    
    return render_template('dashboard.html', licenses=licenses)


@app.route('/api/validate', methods=['POST'])
def validate_license():
    data = request.get_json()
    license_key = data.get('license_key')
    
    conn = sqlite3.connect('licenses.db')
    c = conn.cursor()
    c.execute("SELECT expiry_date, active FROM licenses WHERE license_key = ?", (license_key,))
    license = c.fetchone()
    conn.close()
    
    if license and license[1] == 1 and is_license_valid(license[0]):
        return jsonify({"status": "valid", "expiry_date": license[0]})
    return jsonify({"status": "invalid"})

if __name__ == '__main__':
    init_db()
    app.run(debug=True)