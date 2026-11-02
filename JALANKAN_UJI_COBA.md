# Crushing App — Uji Coba Role Viewer & Cut-off MARIS

## Mulai paling mudah (Windows)
1. Ekstrak ZIP ke folder baru.
2. Klik dua kali `MULAI_CRUSHING_APP.bat`. Skrip membuat `venv` bila belum ada, memasang dependensi, lalu menjalankan `app.py` tanpa perlu menjalankan `Activate.ps1`.
3. Buka `http://127.0.0.1:5000`.

## Menjalankan dari terminal VS Code
Setelah setup pertama selesai, pilih interpreter `venv\Scripts\python.exe` pada VS Code. Buka terminal baru, lalu jalankan `python app.py`.

## Perubahan utama
- Viewer bisa membuka halaman GET sebagai transaction-enabled demo; POST/PUT/PATCH/DELETE ditolak server untuk Viewer.
- Cut-off bersifat fleksibel dan dilakukan Admin MARIS dengan tombol `Selesai Transaksi Crushing Ticket`.
- Penutupan hanya mengambil tiket berstatus `MARIS Completed` yang memiliki nomor MARIS dan belum pernah masuk periode penutupan.
- Tiket yang belum selesai MARIS tetap berada di antrean.
- Riwayat periode menyimpan waktu, pengguna, daftar tiket, dan amount.
- Penghapusan otomatis tiket Approved setelah 24 jam dinonaktifkan.

## Catatan database
File `instance/database.db` dari build lama dipertahankan untuk menghindari masalah login akibat database kosong. Sebelum uji coba, tetap disarankan membuat salinan folder dan database. Jangan menyalin database uji ke aplikasi produksi tanpa pemeriksaan.

## Catatan pengujian
Build ini perlu diuji login dengan akun yang tersedia di database bawaan, kemudian uji tiap role dan proses penutupan. Jangan gunakan transaksi produksi saat uji pertama.
