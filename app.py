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
    url = os.environ.get('DATABASE_URL')
    if url:
        try:
            return psycopg2.connect(url)
        except psycopg2.Error as e:
            print(f"Database connection error: {e}")
            raise
    raise Exception("DATABASE_URL not set")

# تنظیم اولیه دیتابیس
def init_db():
    conn = get_db_connection()
    cur = conn.cursor()
    # ایجاد جدول اگه وجود نداشته باشه
    cur.execute('''CREATE TABLE IF NOT EXISTS licenses
                   (license_key TEXT PRIMARY KEY, expiry_date TEXT, active INTEGER, buyer_name TEXT)''')
    # اضافه کردن ستون‌های جدید اگه وجود نداشته باشن
    cur.execute("ALTER TABLE licenses ADD COLUMN IF NOT EXISTS max_devices INTEGER")
    cur.execute("ALTER TABLE licenses ADD COLUMN IF NOT EXISTS active_devices INTEGER")
    cur.execute("ALTER TABLE licenses ADD COLUMN IF NOT EXISTS device_ids TEXT")
    # ایجاد جدول users
    cur.execute('''CREATE TABLE IF NOT EXISTS users
                   (username TEXT PRIMARY KEY, password TEXT)''')
    hashed_password = hashlib.sha256("amirkma123".encode()).hexdigest()
    cur.execute("INSERT INTO users (username, password) VALUES (%s, %s) ON CONFLICT DO NOTHING", ('amirkma', hashed_password))
    conn.commit()
    cur.close()
    conn.close()

init_db()

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        hashed_password = hashlib.sha256(password.encode()).hexdigest()
        print(f"Attempting login for username: {username}, hashed password: {hashed_password}")
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT * FROM users WHERE username = %s AND password = %s", (username, hashed_password))
        user = cur.fetchone()
        print(f"Database query result: {user}")
        cur.close()
        conn.close()
        if user:
            session['logged_in'] = True
            print("Login successful")
            return redirect(url_for('dashboard'))
        print("Login failed")
        return render_template('login.html', error="نام کاربری یا رمز عبور اشتباه است")
    return render_template('login.html')

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
            max_devices = request.form.get('max_devices', '1')
            try:
                expiry_days = int(expiry_days)
                max_devices = int(max_devices)
            except ValueError:
                expiry_days = 30
                max_devices = 1
            expiry_date = (datetime.now() + timedelta(days=expiry_days)).strftime('%Y-%m-%d')
            buyer_name = request.form.get('buyer_name', 'Unknown')
            cur.execute("INSERT INTO licenses (license_key, expiry_date, active, buyer_name, max_devices, active_devices, device_ids) VALUES (%s, %s, %s, %s, %s, %s, %s)",
                        (license_key, expiry_date, 1, buyer_name, max_devices, 0, ''))
            conn.commit()
        elif 'toggle_active' in request.form:
            license_key = request.form['license_key']
            cur.execute("SELECT active FROM licenses WHERE license_key = %s", (license_key,))
            current_status = cur.fetchone()[0]
            new_status = 0 if current_status else 1
            cur.execute("UPDATE licenses SET active = %s WHERE license_key = %s", (new_status, license_key))
            conn.commit()
        elif 'reset_devices' in request.form:
            license_key = request.form['license_key']
            cur.execute("UPDATE licenses SET active_devices = 0, device_ids = '' WHERE license_key = %s", (license_key,))
            conn.commit()
        elif 'delete' in request.form:
            license_key = request.form['license_key']
            cur.execute("DELETE FROM licenses WHERE license_key = %s", (license_key,))
            conn.commit()
    cur.execute("SELECT license_key, expiry_date, active, buyer_name, max_devices, active_devices FROM licenses")
    licenses = cur.fetchall()
    cur.close()
    conn.close()
    return render_template('dashboard.html', licenses=licenses)

@app.route('/check_license', methods=['POST'])
def check_license():
    license_key = request.form.get('license_key')
    device_id = request.form.get('device_id')
    if not license_key or not device_id:
        return jsonify({'valid': False, 'message': 'No license key or device ID provided'}), 400
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT expiry_date, active, max_devices, active_devices, device_ids FROM licenses WHERE license_key = %s", (license_key,))
    license_data = cur.fetchone()
    cur.close()
    conn.close()
    if license_data:
        expiry_date, active, max_devices, active_devices, device_ids = license_data
        expiry = datetime.strptime(expiry_date, '%Y-%m-%d')
        if active == 1 and expiry >= datetime.now():
            device_ids = device_ids.split(',') if device_ids else []
            if active_devices < max_devices or device_id in device_ids:
                if device_id not in device_ids:
                    device_ids.append(device_id)
                    active_devices += 1
                    conn = get_db_connection()
                    cur = conn.cursor()
                    cur.execute("UPDATE licenses SET device_ids = %s, active_devices = %s WHERE license_key = %s",
                                (','.join(device_ids), active_devices, license_key))
                    conn.commit()
                    cur.close()
                    conn.close()
                return jsonify({'valid': True, 'expiry_date': expiry_date, 'device_allowed': True}), 200
            else:
                return jsonify({'valid': True, 'expiry_date': expiry_date, 'device_allowed': False, 'message': f'Max {max_devices} devices reached'}), 403
        else:
            return jsonify({'valid': False, 'message': 'License expired or inactive'}), 403
    return jsonify({'valid': False, 'message': 'Invalid license key'}), 404

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
