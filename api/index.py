from flask import Flask, request, jsonify
from flask_cors import CORS
from supabase import create_client, Client
import time

app = Flask(__name__)
CORS(app)

# === MASUKKAN KUNCI RAHASIA SUPABASE KAMU DI SINI ===
SUPABASE_URL = "https://gyebaszcfupgdaauobcr.supabase.co"
SUPABASE_KEY = "sb_publishable_l1nNIGmL9qDG6lEUBiwBUA_rDqwLIIu"

# Inisiasi koneksi ke Database Supabase
try:
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
except Exception as e:
    print("Gagal konek ke Supabase:", e)

@app.route('/api/login', methods=['POST'])
def proses_login():
    data = request.json
    user = data.get('username', '').lower().strip()
    pin = data.get('pin', '').strip()

    if not user or not pin:
        return jsonify({"status": "error", "pesan": "Username dan PIN wajib diisi!"}), 400

    # Pintu belakang untuk kamu (Admin)
    if user == 'rahmando._' and pin == '669966':
        return jsonify({"status": "sukses", "is_admin": True})

    try:
        # Cek apakah username sudah pernah mendaftar PIN di database
        res = supabase.table('akun_pengguna').select('*').eq('username', user).execute()
        data_db = res.data

        if len(data_db) == 0:
            # Skenario 1: User belum punya PIN (Pertama kali login)
            # Sistem otomatis mengunci PIN ini selamanya di database
            supabase.table('akun_pengguna').insert({
                "username": user, 
                "pin": pin, 
                "waktu_ban": 0
            }).execute()
            return jsonify({"status": "sukses", "pesan": "PIN baru berhasil dikunci permanen!", "is_admin": False})
        
        else:
            # Skenario 2: User sudah ada di database -> Waktunya interogasi
            user_data = data_db[0]
            
            # Cek kecocokan PIN
            if user_data['pin'] != pin:
                return jsonify({"status": "error", "pesan": "Akses Ditolak! PIN Anda salah / tidak sesuai database."}), 403
            
            # Cek apakah dia sedang dalam masa hukuman (cooldown 1 minggu)
            sekarang = int(time.time() * 1000)
            if user_data['waktu_ban'] > sekarang:
                return jsonify({"status": "banned", "pesan": "Akses diblokir! Anda sedang dalam masa cooldown."}), 403

            # Jika aman semua
            return jsonify({"status": "sukses", "pesan": "Login berhasil", "is_admin": False})

    except Exception as e:
        return jsonify({"status": "error", "pesan": "Kesalahan Server: " + str(e)}), 500


@app.route('/api/kunci_akun', methods=['POST'])
def kunci_akun():
    # Fungsi ini akan dipanggil oleh JavaScript saat timer hasil kurasi habis
    data = request.json
    user = data.get('username', '').lower().strip()
    waktu_ban = data.get('waktu_ban', 0)

    try:
        supabase.table('akun_pengguna').update({"waktu_ban": waktu_ban}).eq('username', user).execute()
        return jsonify({"status": "sukses"})
    except Exception as e:
        return jsonify({"status": "error", "pesan": str(e)}), 500

# Wajib untuk Vercel Serverless
if __name__ == '__main__':
    app.run(debug=True)
  
