import psycopg2
import os
import hashlib
from datetime import datetime, timedelta
from flask import Flask, request, jsonify, render_template, redirect, url_for, session
import secrets

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'your_default_secret_key')

# تابع اتصال به دیتابیس
def get_db_connection():
    url = os.environ.get('DATABASE_URL')  # Render این متغیر رو خودش تنظیم می‌کنه
    if url:
        return psycopg2.connect(url)
    raise Exception("DATABASE_URL not set")

# تنظیم اولیه دیتابیس
def init_db():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('''CREATE TABLE IF NOT EXISTS licenses
                   (license_key TEXT PRIMARY KEY, expiry_date TEXT, active INTEGER, buyer_name TEXT)''')
    cur.execute('''CREATE TABLE IF NOT EXISTS users
                   (username TEXT PRIMARY KEY, password TEXT)''')
    hashed_password = hashlib.sha256("amirkma123".encode()).hexdigest()  # یا رمز دلخواه
    cur.execute("INSERT INTO users (username, password) VALUES (%s, %s) ON CONFLICT DO NOTHING", ('amirkma', hashed_password))
    conn.commit()
    cur.close()
    conn.close()
init_db()
@app.route('/check_license', methods=['POST'])
def check_license():
    license_key = request.form.get('license_key')
    if not license_key:
        return jsonify({'valid': False, 'message': 'No license key provided'}), 400
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT expiry_date, active FROM licenses WHERE license_key = %s", (license_key,))
    license_data = cur.fetchone()
    cur.close()
    conn.close()
    if license_data:
        expiry_date, active = license_data
        if active == 1 and datetime.now().strftime('%Y-%m-%d') <= expiry_date:
            return jsonify({'valid': True, 'expiry_date': expiry_date, 'message': 'License is valid'}), 200
        else:
            return jsonify({'valid': False, 'message': 'License expired or inactive'}), 403
    return jsonify({'valid': False, 'message': 'Invalid license key'}), 404
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        hashed_password = hashlib.sha256(password.encode()).hexdigest()
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT * FROM users WHERE username = %s AND password = %s", (username, hashed_password))
        user = cur.fetchone()
        cur.close()
        conn.close()
        if user:
            session['logged_in'] = True
            return redirect(url_for('dashboard'))
        return render_template('login.html', error="نام کاربری یا رمز عبور اشتباه است")
    return render_template('login.html')
# سایر توابع (login, dashboard, validate_license) رو با get_db_connection به‌روز کن
# مثلاً تابع dashboard:
@app.route('/dashboard', methods=['GET', 'POST'])
def dashboard():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    conn = get_db_connection()
    cur = conn.cursor()
    if request.method == 'POST':
        if 'generate' in request.form:
            license_key = secrets.token_hex(16)
            expiry_days = request.form.get('expiry_days', '30')
            try:
                expiry_days = int(expiry_days)
            except ValueError:
                expiry_days = 30
            expiry_date = (datetime.now() + timedelta(days=expiry_days)).strftime('%Y-%m-%d')
            buyer_name = request.form.get('buyer_name', 'Unknown')
            cur.execute("INSERT INTO licenses (license_key, expiry_date, active, buyer_name) VALUES (%s, %s, %s, %s)",
                        (license_key, expiry_date, 1, buyer_name))
            conn.commit()
        elif 'delete' in request.form:
            license_key = request.form['license_key']
            cur.execute("DELETE FROM licenses WHERE license_key = %s", (license_key,))
            conn.commit()
        elif 'toggle_active' in request.form:
            license_key = request.form['license_key']
            cur.execute("SELECT active FROM licenses WHERE license_key = %s", (license_key,))
            current_status = cur.fetchone()[0]
            new_status = 0 if current_status else 1
            cur.execute("UPDATE licenses SET active = %s WHERE license_key = %s", (new_status, license_key))
            conn.commit()
    cur.execute("SELECT license_key, expiry_date, active, buyer_name FROM licenses")
    licenses = cur.fetchall()
    cur.close()
    conn.close()
    return render_template('dashboard.html', licenses=licenses)
