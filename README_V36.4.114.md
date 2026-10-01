# D-Safe V36.4.114 — Google Drive Test

Basis: **V36.4.113 FINAL**.

## Perubahan yang disengaja
1. Login Google Drive pengguna ditambahkan pada menu **Pengaturan > Penyimpanan Google Drive**.
2. Buku Kerja disimpan per akun pada `D-Safe/Data/buku_kerja_v341.json`.
3. Draft D-Safe dan Safety Talk disimpan per akun pada folder `D-Safe/Draft`.
4. PDF Buku Kerja memiliki tombol **Simpan ke Drive Saya**.
5. PPT D-Safe dan Safety Talk memiliki tombol **Simpan ke Drive Saya** dan **Kirim ke Admin**.
6. **Kirim ke Admin** membuat salinan khusus lalu membagikannya hanya ke email Admin sebagai `reader`. Buku Kerja, foto, TTD, dan draft tidak dibagikan.
7. Reset+Cadangkan tetap menghasilkan ZIP; ketika Drive terhubung, ZIP juga disimpan pada `D-Safe/Cadangan` sebelum reset diizinkan.
8. Pemulihan penuh membuat cadangan sebelum pemulihan di Drive pengguna.
9. Ada pemeriksaan revisi file Drive untuk mengurangi risiko perangkat lama menimpa Buku Kerja yang sudah berubah di perangkat lain.
10. Tanpa konfigurasi Google OAuth, aplikasi tetap memakai perilaku penyimpanan lokal V36.4.113 FINAL.

## Tidak diubah
- Tampilan Beranda dan kartu utama.
- Form Buku Kerja dan aturan kegiatan.
- Dashboard Kinerja.
- Template/algoritme pembuatan PPT D-Safe.
- Template/algoritme pembuatan PPT Safety Talk.
- Layout PDF Buku Kerja.
- Filter reset Tanggal/Bulan/Tahun dan format ZIP lama.

Lihat `GOOGLE_DRIVE_SETUP.md` untuk konfigurasi dan urutan pengujian.
