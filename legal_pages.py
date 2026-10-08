"""Public SAFEGENIX information pages for the Google OAuth consent screen."""

import streamlit as st

APP_HOME = "https://safegenix.streamlit.app/"
PRIVACY_URL = APP_HOME + "?legal=privacy"
TERMS_URL = APP_HOME + "?legal=terms"
SUPPORT_EMAIL = "adminlaporanppt@gmail.com"
UPDATED = "5 Oktober 2026"

PRIVACY_TEXT = """
SAFEGENIX membantu Kepala Stasiun mencatat kegiatan keselamatan melalui Buku Kerja,
kemudian menghasilkan Buku Kerja PDF, PPT D-Safe bulanan, dan PPT Safety Talk mingguan.
Kebijakan ini menjelaskan pengolahan data pada aplikasi utama dan pengelolaan laporan
melalui SAFEGENIX Admin.

### 1. Data dan tujuan penggunaannya

- **Identitas Google:** alamat email, nama, dan informasi profil digunakan untuk
  mengenali akun, menghubungkan Google Drive, serta mencocokkan persetujuan admin.
- **Profil pengguna dan petugas:** nama, NIPP, stasiun, serta nama petugas yang Anda
  masukkan digunakan untuk identitas Buku Kerja, laporan, dan rekap kegiatan.
- **Data kegiatan:** tanggal, uraian, peserta, foto, dan tanda tangan yang Anda
  masukkan digunakan untuk dokumentasi, laporan, dashboard, cadangan, dan pemulihan.
- **Daftar akses:** email, nama, stasiun, informasi profil, status akun, dan riwayat
  perubahan digunakan pengelola untuk menyetujui, menonaktifkan, atau menghapus akun.

### 2. Akses Google Drive

Aplikasi utama meminta izin `drive.file`, dengan akses terbatas pada berkas yang
dibuat atau dibuka menggunakan SAFEGENIX. Izin ini digunakan untuk membaca dan
menyimpan data aplikasi, membuat folder, menyimpan laporan dan cadangan, memulihkan
data, serta membagikan salinan PPT yang Anda kirim kepada admin.

SAFEGENIX Admin menggunakan izin Drive untuk menemukan laporan yang dibagikan
kepada akun admin, mengatur salinannya menurut jenis dan periode, serta menyimpan
hasil penggabungan PPT. Akses admin berlaku pada berkas yang dapat diakses akun
Google admin tersebut.

### 3. Penyimpanan dan penerima data

Data kerja dan cadangan disimpan pada Google Drive akun pengguna. Data yang sedang
diproses juga berada dalam sesi aplikasi di server. Daftar persetujuan akun dikelola
pada repositori privat pengelola. Browser menyimpan informasi sesi dan draft;
informasi koneksi Google yang dipertahankan di browser disimpan dalam bentuk terenkripsi.

Ketika Anda menekan **Kirim ke Admin**, aplikasi membagikan salinan PPT kepada akun
admin yang dikonfigurasi. Admin dapat mengunduh, menyalin, mengelompokkan, dan
menggabungkan laporan tersebut. Tanda tangan digunakan pada Buku Kerja PDF.

Google menyediakan autentikasi dan Drive; Streamlit menjalankan aplikasi;
GitHub menyediakan kode dan penyimpanan privat daftar akses. Masing-masing layanan
juga memproses data sesuai kebijakan dan pengaturan layanan mereka.

### 4. Penggunaan terbatas dan perlindungan

Data digunakan untuk autentikasi, pengaturan akses, dan fungsi pencatatan serta
pelaporan yang dijelaskan di atas. Data Google tidak digunakan untuk iklan,
dijual, atau digunakan untuk melatih model AI.

Penggunaan dan penerusan informasi yang diterima dari Google API mengikuti
[Google API Services User Data Policy](https://developers.google.com/terms/api-services-user-data-policy),
termasuk persyaratan **Limited Use**.

Akses fitur pengguna memerlukan login dan persetujuan admin. Akses aplikasi admin
dibatasi ke akun admin yang dikonfigurasi. Kendali ini melindungi akses aplikasi;
salinan laporan yang telah dibagikan mengikuti izin penyimpanan dan penerimanya.

### 5. Kendali, masa simpan, dan penghapusan

Anda dapat mengoreksi atau menghapus kegiatan melalui aplikasi, mengelola berkas
pada Drive, keluar melalui Pengaturan, serta mencabut izin SAFEGENIX melalui
[koneksi akun Google](https://myaccount.google.com/connections).

Data dipertahankan selama masih tersimpan pada aplikasi, Drive, daftar akses,
atau arsip pengelola. **Reset Data** menyimpan salinan pemulihan secara otomatis sebelum mengosongkan
data kegiatan aktif. Cadangan, keluaran yang pernah dibuat, salinan admin, dan
riwayat versi pada layanan penyimpanan perlu dikelola secara terpisah.
Keluar dari aplikasi atau mencabut izin Google tidak otomatis menghapus berkas
Drive maupun salinan laporan admin.

Untuk permintaan penghapusan akun atau data yang dikelola admin, hubungi pengelola
melalui alamat kontak di bawah. Penghapusan kegiatan dan penonaktifan akun merupakan
tindakan yang berbeda.

### 6. Kontak dan perubahan

Pengelola SAFEGENIX dapat dihubungi melalui **adminlaporanppt@gmail.com**.
Pertanyaan tentang akses, penggunaan data, koreksi, atau penghapusan data dapat
disampaikan melalui alamat tersebut. Pembaruan kebijakan ditampilkan pada halaman
ini bersama tanggal pembaruannya.
"""

TERMS_TEXT = """
SAFEGENIX digunakan oleh Kepala Stasiun untuk mencatat kegiatan keselamatan operasi
dan membuat laporan dari satu sumber input pada Buku Kerja.

### 1. Akun dan akses

Masuk menggunakan akun Google milik Anda, lengkapi nama pengguna, stasiun, dan NIPP,
lalu ajukan akses kepada admin. Persetujuan admin berlaku selama akun tetap aktif.
Saat masuk kembali dengan Gmail yang sama, persetujuan tersebut tetap digunakan.
Google dapat meminta autentikasi atau persetujuan izin kembali sesuai status
koneksi akun Anda. Admin mengelola persetujuan, penonaktifan, dan penghapusan akun.

### 2. Data dan tanggung jawab pengguna

Masukkan data sesuai kegiatan yang dilaksanakan. Gunakan foto dan tanda tangan
yang berhak Anda gunakan, serta pastikan petugas yang bersangkutan mengetahui
penggunaannya untuk dokumentasi dan pelaporan. Periksa tanggal, periode, identitas,
isi, dan dokumentasi sebelum menyimpan, mengunduh, atau mengirim laporan.

### 3. Laporan dan pengiriman

SAFEGENIX menghasilkan Buku Kerja PDF, PPT D-Safe bulanan, dan PPT Safety Talk
mingguan berdasarkan input dan periode yang dipilih. Tombol **Kirim ke Admin**
menyerahkan salinan PPT kepada admin. Admin mengelola laporan menurut jenis dan
periode, serta dapat menggabungkan PPT yang sesuai. Gunakan **Edit** untuk
mengoreksi sumber data, lalu buat ulang laporan yang perlu diperbarui.

### 4. Penyimpanan dan pemulihan

Penggunaan online memerlukan koneksi internet dan akses Google Drive yang aktif.
Periksa hasil penyimpanan dan pengiriman. Kelola cadangan sesuai kebutuhan;
pemulihan menggunakan data dari cadangan yang Anda pilih. Cadangan dan salinan
laporan yang telah dibagikan dikelola terpisah dari data kegiatan aktif.

### 5. Privasi dan bantuan

Pengolahan data dijelaskan pada
[Kebijakan Privasi SAFEGENIX](https://safegenix.streamlit.app/?legal=privacy).
Hubungi **adminlaporanppt@gmail.com** untuk bantuan akun, laporan, atau pengelolaan
data. Pembaruan ketentuan ditampilkan pada halaman ini bersama tanggal pembaruannya.
"""


def render_legal_page_if_requested():
    """Render only public information; never request account or Drive data."""
    page = st.query_params.get("legal")
    if page not in ("privacy", "terms"):
        return False

    st.markdown("""
    <style>
    .block-container {max-width:900px !important; padding-top:1.2rem !important;}
    [data-testid="stMarkdownContainer"] {line-height:1.65;}
    </style>
    """, unsafe_allow_html=True)
    st.markdown("**SAFEGENIX** · Pencatatan dan laporan keselamatan operasi")
    st.title("Kebijakan Privasi" if page == "privacy" else "Ketentuan Penggunaan")
    st.caption("Terakhir diperbarui: " + UPDATED)
    st.markdown(PRIVACY_TEXT if page == "privacy" else TERMS_TEXT)
    st.markdown(
        f"[Beranda SAFEGENIX]({APP_HOME}) · "
        f"[Kebijakan Privasi]({PRIVACY_URL}) · "
        f"[Ketentuan Penggunaan]({TERMS_URL})"
    )
    return True


def render_legal_footer():
    """Link the policies from the existing public Beranda."""
    st.markdown(
        '<div style="text-align:center;font-size:.75rem;padding:.2rem 0;">'
        f'<a href="{PRIVACY_URL}" target="_self">Kebijakan Privasi</a>'
        ' &nbsp;·&nbsp; '
        f'<a href="{TERMS_URL}" target="_self">Ketentuan Penggunaan</a>'
        '</div>',
        unsafe_allow_html=True,
    )
