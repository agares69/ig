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
        # 1. Ambil IP Asli user
        ip_user = request.headers.get('X-Real-IP', request.headers.get('X-Forwarded-For', request.remote_addr))
        if ip_user and ',' in ip_user:
            ip_user = ip_user.split(',')[0].strip()

        # 2. Cek Blacklist IP
        url_cek_blacklist = f"{SUPABASE_URL}/rest/v1/ip_blacklist?ip=eq.{ip_user}"
        response_blacklist = requests.get(url_cek_blacklist, headers=HEADERS)
        data_blacklist = response_blacklist.json()

        if len(data_blacklist) > 0:
            return jsonify({"status": "error", "pesan": "Akses Ditolak! Perangkat atau jaringan Anda diblokir karena tindakan kecurangan."}), 403

        # 3. Cek User di database akun_pengguna
        url_select = f"{SUPABASE_URL}/rest/v1/akun_pengguna?username=eq.{user}"
        response_select = requests.get(url_select, headers=HEADERS)
        data_db = response_select.json()

        if len(data_db) == 0:
            # Skenario 1: User baru -> Daftarkan dan set waktu_kurasi awal = 0
            url_insert = f"{SUPABASE_URL}/rest/v1/akun_pengguna"
            payload = {"username": user, "pin": pin, "waktu_ban": 0, "ip_terakhir": ip_user, "waktu_kurasi": 0}
            requests.post(url_insert, headers=HEADERS, json=payload)
            
            return jsonify({"status": "sukses", "pesan": "PIN baru berhasil dikunci permanen!", "is_admin": False})
        
        else:
            # Skenario 2: User sudah terdaftar
            user_data = data_db[0]
            
            if user_data['pin'] != pin:
                return jsonify({"status": "error", "pesan": "Akses Ditolak! PIN salah."}), 403
            
            sekarang = int(time.time() * 1000)
            if user_data['waktu_ban'] > sekarang:
                return jsonify({"status": "banned", "pesan": "Akses diblokir! Sedang dalam masa cooldown."}), 403

            # ✨ FITUR PEMULIHAN: Jika user ganti browser/hapus data tapi waktu kurasi di DB masih aktif
            waktu_kurasi = user_data.get('waktu_kurasi', 0)
            if waktu_kurasi and waktu_kurasi > sekarang:
                url_update_ip = f"{SUPABASE_URL}/rest/v1/akun_pengguna?username=eq.{user}"
                requests.patch(url_update_ip, headers=HEADERS, json={"ip_terakhir": ip_user})
                
                return jsonify({
                    "status": "lanjut_timer", 
                    "pesan": "Sesi aktif ditemukan.", 
                    "waktu_target": waktu_kurasi,
                    "is_admin": False
                })

            # Jika login biasa tanpa ada sesi berjalan
            url_update_ip = f"{SUPABASE_URL}/rest/v1/akun_pengguna?username=eq.{user}"
            requests.patch(url_update_ip, headers=HEADERS, json={"ip_terakhir": ip_user})

            return jsonify({"status": "sukses", "pesan": "Login berhasil", "is_admin": False})

    except Exception as e:
        return jsonify({"status": "error", "pesan": "Kesalahan HTTP: " + str(e)}), 500


@app.route('/api/mulai_kurasi', methods=['POST'])
def mulai_kurasi():
    data = request.json
    if not data:
        return jsonify({"status": "error", "pesan": "Data tidak lengkap"}), 400
        
    user = data.get('username', '').lower().strip()
    waktu_target = data.get('waktu_target')

    try:
        url_update = f"{SUPABASE_URL}/rest/v1/akun_pengguna?username=eq.{user}"
        requests.patch(url_update, headers=HEADERS, json={"waktu_kurasi": waktu_target})
        return jsonify({"status": "sukses"})
    except Exception as e:
        return jsonify({"status": "error", "pesan": str(e)}), 500


@app.route('/api/kunci_akun', methods=['POST'])
def kunci_akun():
    data = request.json
    if not data:
        return jsonify({"status": "error"}), 400
        
    user = data.get('username', '').lower().strip()
    waktu_ban = data.get('waktu_ban', 0)

    try:
        # Saat waktu habis, set waktu_ban seminggu dan bersihkan waktu_kurasi ke 0 lagi
        url_update = f"{SUPABASE_URL}/rest/v1/akun_pengguna?username=eq.{user}"
        requests.patch(url_update, headers=HEADERS, json={"waktu_ban": waktu_ban, "waktu_kurasi": 0})
        return jsonify({"status": "sukses"})
    except Exception as e:
        return jsonify({"status": "error", "pesan": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)
