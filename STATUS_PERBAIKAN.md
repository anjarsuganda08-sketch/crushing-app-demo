STATUS PAKET DEMO — 2 NOVEMBER 2026

Perubahan yang sudah diterapkan pada paket ini:
1. Navigasi Demo Admin menampilkan seluruh menu utama dalam satu sesi.
2. Master part dummy menggunakan harga contoh: A Rp12.500, B Rp18.750, C Rp25.000.
3. Paket tetap memakai akun demo publik dan data part fiktif yang disiapkan oleh app.py.
4. app.py berhasil melewati pemeriksaan sintaks Python.

PENTING — kandidat untuk pengujian, belum dinyatakan siap produksi/publik:
- Belum dilakukan pengujian runtime menyeluruh pada semua alur Production → Pulling → Monitoring/Leader → MARIS → Export.
- Badge notifikasi dinamis per antrean dan reset database demo terjadwal belum diimplementasikan/diuji sepenuhnya dalam paket ini.
- Sebelum dipublikasikan, audit semua endpoint admin/import dan konfigurasi deployment serta uji akses publik perlu dilakukan.
- Gunakan hanya data dummy. Jangan menambahkan database, foto part, atau informasi perusahaan yang asli.

Menjalankan lokal: baca README_PUBLIC_DEMO.md dan JALANKAN_UJI_COBA.md terlebih dahulu.


UPDATE AKSES DEMO ADMIN — 2 NOVEMBER 2026
- Memperbaiki pemeriksaan role agar akun public_demo_operator dapat membuka halaman alur Pulling, Monitoring, dan MARIS tanpa berpindah akun.
- Mengizinkan POST pada jalur alur transaksi demo; endpoint impor/pengelolaan akun tetap diblokir.
- Ini perbaikan terarah dan belum menggantikan pengujian runtime end-to-end. Uji semua tombol/status sebelum dipublikasikan.
