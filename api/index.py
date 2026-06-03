from flask import Flask, request, jsonify
from flask_cors import CORS
import requests  
import time

app = Flask(__name__)
CORS(app)

# === KUNCI SUPABASE KAMU ===
SUPABASE_URL = "https://gyebaszcfupgdaauobcr.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Imd5ZWJhc3pjZnVwZ2RhYXVvYmNyIiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODA0MzEyMjcsImV4cCI6MjA5NjAwNzIyN30.hYBwSpJ4yro8BzG2GzpDIWnOoPkqWXr9xefeNUAHhz8"

HEADERS = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json",
    "Prefer": "return=representation"
}

@app.route('/api/login', methods=['POST'])
def proses_login():
    data = request.json
    if not data:
        return jsonify({"status": "error", "pesan": "Data tidak dikirim oleh frontend!"}), 400

    user = data.get('username', '').lower().strip()
    pin = data.get('pin', '').strip()

    if not user or not pin:
        return jsonify({"status": "error", "pesan": "Username dan PIN wajib diisi!"}), 400

    if user == 'rahmando._' and pin == '669966':
        return jsonify({"status": "sukses", "is_admin": True})

    try:
        # 1. Mengambil IP Asli user
        ip_user = request.headers.get('X-Real-IP', request.headers.get('X-Forwarded-For', request.remote_addr))
        if ip_user and ',' in ip_user:
            ip_user = ip_user.split(',')[0].strip()

        # 🔥 LOGIKA BARU: Cek apakah IP ini terdaftar di Blacklist
        url_cek_blacklist = f"{SUPABASE_URL}/rest/v1/ip_blacklist?ip=eq.{ip_user}"
        response_blacklist = requests.get(url_cek_blacklist, headers=HEADERS)
        data_blacklist = response_blacklist.json()

        if len(data_blacklist) > 0:
            # Jika IP ditemukan di tabel blacklist, LANGSUNG BLOKIR DI TEMPAT!
            return jsonify({"status": "error", "pesan": "Akses Ditolak! Perangkat atau jaringan Anda diblokir karena tindakan kecurangan."}), 403


        # 2. CEK USER (SELECT) lewat jalur HTTP REST API (Proses Normal)
        url_select = f"{SUPABASE_URL}/rest/v1/akun_pengguna?username=eq.{user}"
        response_select = requests.get(url_select, headers=HEADERS)
        data_db = response_select.json()

        if len(data_db) == 0:
            # Skenario 1: User belum terdaftar -> SIMPAN DATA BARU (INSERT)
            url_insert = f"{SUPABASE_URL}/rest/v1/akun_pengguna"
            payload = {"username": user, "pin": pin, "waktu_ban": 0, "ip_terakhir": ip_user}
            requests.post(url_insert, headers=HEADERS, json=payload)
            
            return jsonify({"status": "sukses", "pesan": "PIN baru berhasil dikunci permanen!", "is_admin": False})
        
        else:
            # Skenario 2: User sudah ada
            user_data = data_db[0]
            
            if user_data['pin'] != pin:
                return jsonify({"status": "error", "pesan": "Akses Ditolak! PIN salah."}), 403
            
            sekarang = int(time.time() * 1000)
            if user_data['waktu_ban'] > sekarang:
                return jsonify({"status": "banned", "pesan": "Akses diblokir! Sedang dalam masa cooldown."}), 403

            # Update IP terbaru mereka jika sukses login
            url_update_ip = f"{SUPABASE_URL}/rest/v1/akun_pengguna?username=eq.{user}"
            requests.patch(url_update_ip, headers=HEADERS, json={"ip_terakhir": ip_user})

            return jsonify({"status": "sukses", "pesan": "Login berhasil", "is_admin": False})

    except Exception as e:
        return jsonify({"status": "error", "pesan": "Kesalahan HTTP: " + str(e)}), 500


@app.route('/api/kunci_akun', methods=['POST'])
def kunci_akun():
    data = request.json
    if not data:
        return jsonify({"status": "error"}), 400
        
    user = data.get('username', '').lower().strip()
    waktu_ban = data.get('waktu_ban', 0)

    try:
        # UPDATE data lewat HTTP REST API
        url_update = f"{SUPABASE_URL}/rest/v1/akun_pengguna?username=eq.{user}"
        requests.patch(url_update, headers=HEADERS, json={"waktu_ban": waktu_ban})
        return jsonify({"status": "sukses"})
    except Exception as e:
        return jsonify({"status": "error", "pesan": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)
    
