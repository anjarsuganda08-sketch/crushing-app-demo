# Crushing App — Final Build

## Perubahan utama

1. **Production multi-part**
   - Pilih beberapa part sekaligus.
   - Tombol **Pilih Semua** untuk memasukkan seluruh komponen pada satu Model.
   - Pencarian part berdasarkan nama atau Part Number.
   - Qty setiap part dapat diedit setelah dipilih.
   - Total Qty ditampilkan sebelum part dimasukkan ke ticket.
   - Jenis NG dan Shift tetap berlaku untuk batch part yang dipilih.

2. **Identitas operator**
   - Setiap ticket baru menyimpan NPK dan nama operator berdasarkan account yang login.
   - Export mengambil NIK/NPK dan Operator Name dari ticket, bukan lagi nilai default "Operator Produksi".
   - Database lama akan otomatis menambahkan kolom operator saat aplikasi pertama kali dijalankan.

3. **Dashboard**
   - Panel account aktif dibuat menjadi welcome card profesional: "Hallo, [Nickname]!".
   - Menampilkan NPK, role, nama lengkap, dan status sistem.

4. **Top Navigation**
   - Navigasi dibuat konsisten dan memiliki indikator halaman aktif.
   - Master Part dibuat menjadi halaman master data yang lebih profesional dengan pencarian.
   - Member Import, Master Import, dan Export tetap tersedia untuk **Admin** dan **MARIS**.

5. **Authentication**
   - Struktur role tetap menggunakan: admin, operator, pulling, leader, viewer, maris.

## Menjalankan di Windows / VS Code

Buka terminal PowerShell di folder project.

### Cara paling aman tanpa mengaktifkan venv

```powershell
python -m venv venv
venv\Scripts\python.exe -m pip install -r requirements.txt
venv\Scripts\python.exe app.py
```

Jika PowerShell memblokir `Activate.ps1`, tidak perlu mengubah policy Windows. Jalankan langsung:

```powershell
venv\Scripts\python.exe app.py
```

Kemudian buka browser ke:

`http://127.0.0.1:5000`

### Jika ingin mengaktifkan venv

Untuk sesi PowerShell saat itu saja:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
venv\Scripts\Activate.ps1
python app.py
```

## Catatan database

File `instance/database.db` dipertahankan. Saat build final dijalankan, aplikasi memeriksa kolom baru pada `crushing_ticket` dan menambahkannya jika belum ada. Data lama tidak dihapus.
