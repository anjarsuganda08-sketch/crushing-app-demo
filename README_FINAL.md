# Crushing App — Final

Crushing Validation System untuk alur Production → Pulling → Leader → MARIS → Reporting.

## Perbaikan utama versi final

- Memperbaiki crash Flask `View function mapping is overwriting an existing endpoint function: auth.logout` dengan menghapus duplikasi route `/auth/logout`.
- Logout sekarang menghapus session dan device cookie sehingga tidak langsung auto-login kembali.
- Role `maris` mendapat akses penuh ke fungsi data import/export yang relevan: Master Part import, Member import, Download Master Part, Export Crushing, dan Admin MARIS export.
- Menambahkan proteksi role pada endpoint workflow utama.
- Menambahkan navigasi aplikasi yang konsisten dan responsif untuk user yang sudah login.
- Menambahkan styling global yang lebih elegan/profesional tanpa menghilangkan tampilan khusus halaman yang sudah ada.
- Root `/` tidak lagi menampilkan KPI dummy; user diarahkan ke Dashboard bila login atau Login bila belum.
- Endpoint maintenance/migration lama dibatasi untuk Admin.
- Menambahkan `requirements.txt`.

## Menjalankan aplikasi

1. Buka terminal pada folder project.
2. Buat/aktifkan virtual environment.
3. Install dependency:

```bash
pip install -r requirements.txt
```

4. Jalankan:

```bash
python app.py
```

Database aktif berada di `instance/database.db`. Backup database lama berada di folder `backup/`.

## Catatan keamanan

Untuk deployment, set environment variable `CRUSHING_SECRET_KEY` dengan secret key yang kuat. Jangan memakai secret key default pada server production.

Cookie device menggunakan HttpOnly + SameSite=Lax dan akan menggunakan Secure otomatis ketika request berjalan melalui HTTPS.
