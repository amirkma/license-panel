import psycopg2
import os
import hashlib
from datetime import datetime, timedelta
from flask import Flask, request, jsonify, render_template, redirect, url_for, session

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'your_default_secret_key')  # متغیر محیطی

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
            expiry_days = int(request.form['expiry_days'])
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

# سایر روت‌ها (مثل login و validate_license) هم همین‌طور به‌روز کن
