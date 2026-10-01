# D-Safe V36.4.113 — Google Drive per pengguna

Versi ini mempertahankan UI/fungsi V36.4.113 FINAL dan menambahkan penyimpanan Google Drive per pengguna.

## Yang disimpan ke Drive pengguna
- `D-Safe/Data/buku_kerja_v341.json` — Buku Kerja, termasuk foto dan tanda tangan yang memang berada pada payload Buku Kerja.
- `D-Safe/Draft/` — draft D-Safe dan Safety Talk.
- `D-Safe/Output Buku Kerja/` — PDF yang dipilih pengguna untuk disimpan.
- `D-Safe/Output D-Safe/` — PPT D-Safe yang dipilih pengguna untuk disimpan.
- `D-Safe/Output Safety Talk/` — PPT Safety Talk yang dipilih pengguna untuk disimpan.
- `D-Safe/Cadangan/` — cadangan otomatis sebelum pemulihan penuh.
- `D-Safe/Terkirim ke Admin/` — salinan PPT yang secara eksplisit dikirim pengguna kepada Admin.

## Privasi
Aplikasi meminta scope Google Drive `drive.file`, bukan akses penuh ke seluruh Drive. Admin hanya menerima salinan PPT yang pengguna pilih lewat tombol **Kirim ke Admin**. Buku Kerja, foto, tanda tangan, dan draft tidak dibagikan kepada Admin.

## Konfigurasi Google Cloud
1. Buat/ pilih project Google Cloud.
2. Aktifkan **Google Drive API**.
3. Konfigurasikan OAuth consent screen.
4. Buat OAuth Client ID jenis **Web application**.
5. Tambahkan redirect URI yang akan dipakai:
   - Uji lokal Windows: `http://localhost:8501/`
   - Streamlit Cloud: `https://nama-aplikasi.streamlit.app/`
   Nilai `redirect_uri` pada Secrets harus persis sama dengan salah satu URI yang didaftarkan.
6. Untuk masa pengujian, tambahkan akun pengguna sebagai Test users bila consent screen masih dalam mode Testing.

## Streamlit Secrets
Salin `.streamlit/secrets.toml.example` menjadi konfigurasi Secrets pada Streamlit Community Cloud dan isi nilainya.

`admin_email` adalah akun Google Admin yang akan menerima PPT dari seluruh pengguna melalui Google Drive **Shared with me**. Admin tidak perlu login ke aplikasi untuk menerima file.

## Alur pengujian
1. Buka aplikasi > Pengaturan > Penyimpanan Google Drive.
2. Tekan **Hubungkan Google Drive** dan login memakai akun pengguna.
3. Simpan satu kegiatan Buku Kerja, tutup/buka ulang halaman, lalu pastikan kegiatan tetap ada setelah login ulang.
4. Cetak PDF Buku Kerja > **Simpan ke Drive Saya**.
5. Generate D-Safe > **Simpan ke Drive Saya** > **Kirim ke Admin**.
6. Generate Safety Talk > **Simpan ke Drive Saya** > **Kirim ke Admin**.
7. Login ke akun Admin dan periksa **Shared with me**. Hanya PPT yang dikirim harus terlihat.
8. Uji Reset dan Cadangkan serta Pulihkan Cadangan seperti versi FINAL.

## Catatan sesi login
Token OAuth hanya disimpan pada sesi Streamlit, tidak ditulis ke server/repo. Bila sesi server baru dibuat, pengguna perlu menghubungkan Google Drive kembali. Data permanen tetap aman di Drive pengguna.
