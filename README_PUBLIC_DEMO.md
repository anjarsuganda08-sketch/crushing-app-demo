# Crushing App — NG Material Control (Public Demo Candidate)

Ini adalah paket kandidat demo publik dengan data fiktif. Jangan gunakan untuk data operasional atau informasi pribadi.

## Jalankan secara lokal

1. Gunakan Python 3.13 atau versi kompatibel.
2. Buat virtual environment: `python -m venv .venv`
3. Aktifkan environment, lalu jalankan: `pip install -r requirements.txt`
4. Atur `CRUSHING_SECRET_KEY` dengan nilai acak yang panjang (lihat `.env.example`; jangan commit file `.env`).
5. Jalankan `python app.py` jika app.py memiliki entry point lokal; atau `gunicorn app:app`.
6. Buka alamat lokal yang ditampilkan Flask dan pilih Coba Demo.

Aplikasi akan membuat skema database dan seed data demo fiktif saat startup. Folder `instance/` dan file database tidak disertakan dalam paket ini agar database lokal tidak ikut dipublikasikan.

## Render

File `render.yaml` menyediakan konfigurasi awal. Setelah repositori dihubungkan ke Render, periksa build/start command dan environment variables pada dashboard. Penyimpanan SQLite lokal pada hosting dapat bersifat sementara dan tidak cocok untuk data yang harus persisten; demo ini harus diperlakukan sebagai data sementara sampai mekanisme persistensi/reset dikonfigurasi.

## Batasan dan pemeriksaan sebelum publikasi

Paket ini belum dinyatakan production-ready. Sebelum membuat repositori publik:
- audit seluruh endpoint dan aturan akses; akun demo boleh menjalankan alur transaksi demo saja, bukan mengubah akun, impor data, atau pengaturan sensitif;
- uji alur Production → Pulling → Need Leader → MARIS → Export pada lingkungan hosting;
- verifikasi badge notifikasi terhadap status antrean sebenarnya;
- pastikan tidak ada data perusahaan, foto, database, backup, token, atau password asli;
- siapkan reset database demo dengan cara yang aman dan terjadwal bila diperlukan.

Semua transaksi demo dianggap dapat dilihat oleh pengunjung lain pada instance yang sama. Jangan masukkan informasi pribadi atau rahasia.
