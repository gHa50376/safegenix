"""Google Drive storage bridge for D-Safe V36.4.113.

Design goals:
- Keep the original D-Safe UI and report generators intact.
- Each user authorizes their own Google Drive with the narrow ``drive.file`` scope.
- Application data is never persisted as a shared server-side data file when cloud mode is enabled.
- OAuth credentials live only in the current Streamlit session. Users reconnect after a new server session.
- PPT files are sent to the configured admin by sharing a dedicated copy; the admin never gets access
  to Buku Kerja, photos, signatures, drafts, or the user's other Drive files.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import io
import json
import os
import re
import secrets as pysecrets
import time
from datetime import datetime, timedelta, timezone
from pathlib import PurePosixPath
from typing import Optional

import streamlit as st

try:
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import Flow
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaIoBaseDownload, MediaIoBaseUpload
except Exception:  # local legacy mode still starts without Google packages
    Request = Credentials = Flow = build = MediaIoBaseDownload = MediaIoBaseUpload = None

SCOPES = [
    "openid",
    "https://www.googleapis.com/auth/userinfo.email",
    "https://www.googleapis.com/auth/userinfo.profile",
    "https://www.googleapis.com/auth/drive.file",
]
ROOT_FOLDER = "D-Safe"
FOLDER_MIME = "application/vnd.google-apps.folder"
_STATE_TTL_SECONDS = 15 * 60


def _cfg() -> dict:
    try:
        section = st.secrets.get("google_oauth", {})
        return dict(section) if section else {}
    except Exception:
        return {}


def cloud_enabled() -> bool:
    c = _cfg()
    return bool(c.get("client_id") and c.get("client_secret") and c.get("redirect_uri"))


def admin_configured() -> bool:
    return bool(str(_cfg().get("admin_email") or "").strip())


def _libs_available() -> bool:
    return all(x is not None for x in (Request, Credentials, Flow, build, MediaIoBaseUpload))


def _client_config() -> dict:
    c = _cfg()
    return {
        "web": {
            "client_id": str(c.get("client_id") or ""),
            "client_secret": str(c.get("client_secret") or ""),
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
        }
    }


def _state_key() -> bytes:
    c = _cfg()
    value = str(c.get("state_secret") or c.get("client_secret") or "dsafe-oauth-state")
    return value.encode("utf-8")


def _b64u(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode("ascii").rstrip("=")


def _b64u_decode(data: str) -> bytes:
    return base64.urlsafe_b64decode(data + "=" * (-len(data) % 4))


def _make_state() -> str:
    payload = json.dumps(
        {"ts": int(time.time()), "nonce": pysecrets.token_urlsafe(12)},
        separators=(",", ":"),
    ).encode("utf-8")
    sig = hmac.new(_state_key(), payload, hashlib.sha256).digest()
    return f"{_b64u(payload)}.{_b64u(sig)}"


def _valid_state(state: str) -> bool:
    try:
        p, s = state.split(".", 1)
        payload = _b64u_decode(p)
        sig = _b64u_decode(s)
        if not hmac.compare_digest(hmac.new(_state_key(), payload, hashlib.sha256).digest(), sig):
            return False
        obj = json.loads(payload.decode("utf-8"))
        age = int(time.time()) - int(obj["ts"])
        return 0 <= age <= _STATE_TTL_SECONDS
    except Exception:
        return False


def authorization_url() -> Optional[str]:
    if not cloud_enabled() or not _libs_available():
        return None
    flow = Flow.from_client_config(_client_config(), scopes=SCOPES, autogenerate_code_verifier=False)
    flow.redirect_uri = str(_cfg()["redirect_uri"])
    state = _make_state()
    url, _ = flow.authorization_url(
        access_type="offline",
        include_granted_scopes="true",
        prompt="consent",
        state=state,
    )
    return url


def _serialize_credentials(creds) -> dict:
    return {
        "token": creds.token,
        "refresh_token": creds.refresh_token,
        "token_uri": creds.token_uri,
        "client_id": creds.client_id,
        "client_secret": creds.client_secret,
        "scopes": list(creds.scopes or SCOPES),
    }


def _credentials():
    info = st.session_state.get("_gdrive_credentials")
    if not info or Credentials is None:
        return None
    try:
        creds = Credentials.from_authorized_user_info(info, scopes=SCOPES)
        if creds.expired and creds.refresh_token:
            creds.refresh(Request())
            st.session_state["_gdrive_credentials"] = _serialize_credentials(creds)
        return creds
    except Exception as exc:
        st.session_state["_gdrive_auth_error"] = f"Sesi Google Drive perlu dihubungkan ulang: {exc}"
        return None


def connected() -> bool:
    return _credentials() is not None


def _service():
    creds = _credentials()
    if creds is None:
        raise RuntimeError("Google Drive belum terhubung.")
    return build("drive", "v3", credentials=creds, cache_discovery=False)


def _cache() -> dict:
    return st.session_state.setdefault("_gdrive_bytes_cache", {})


def _ids() -> dict:
    return st.session_state.setdefault("_gdrive_file_ids", {})


def _pending() -> dict:
    return st.session_state.setdefault("_gdrive_pending", {})


def _versions() -> dict:
    return st.session_state.setdefault("_gdrive_versions", {})


def _esc(value: str) -> str:
    return str(value).replace("\\", "\\\\").replace("'", "\\'")


def _find_child(service, parent_id: str, name: str, mime_type: Optional[str] = None):
    q = [f"'{_esc(parent_id)}' in parents", f"name = '{_esc(name)}'", "trashed = false"]
    if mime_type:
        q.append(f"mimeType = '{_esc(mime_type)}'")
    result = service.files().list(
        q=" and ".join(q),
        spaces="drive",
        fields="files(id,name,mimeType,modifiedTime,version)",
        pageSize=20,
    ).execute()
    files = result.get("files", [])
    return files[0] if files else None


def _ensure_folder(service, parent_id: str, name: str) -> str:
    found = _find_child(service, parent_id, name, FOLDER_MIME)
    if found:
        return found["id"]
    created = service.files().create(
        body={"name": name, "mimeType": FOLDER_MIME, "parents": [parent_id]},
        fields="id",
    ).execute()
    return created["id"]


def _ensure_path_folders(service, parts) -> str:
    root = st.session_state.get("_gdrive_root_id")
    if not root:
        found = _find_child(service, "root", ROOT_FOLDER, FOLDER_MIME)
        root = found["id"] if found else _ensure_folder(service, "root", ROOT_FOLDER)
        st.session_state["_gdrive_root_id"] = root
    parent = root
    for part in parts:
        key = f"folder:{parent}:{part}"
        cached = _ids().get(key)
        if cached:
            parent = cached
            continue
        parent = _ensure_folder(service, parent, part)
        _ids()[key] = parent
    return parent


def _locate_file(service, rel_path: str):
    rel = PurePosixPath(rel_path)
    parent = _ensure_path_folders(service, rel.parts[:-1])
    key = f"file:{rel_path}"
    cached = _ids().get(key)
    if cached:
        return {"id": cached, "name": rel.name}, parent
    found = _find_child(service, parent, rel.name)
    if found:
        _ids()[key] = found["id"]
    return found, parent


def read_bytes(rel_path: str, *, refresh: bool = False) -> Optional[bytes]:
    rel_path = str(PurePosixPath(rel_path))
    if not connected():
        return st.session_state.setdefault("_gdrive_guest_files", {}).get(rel_path)
    if not refresh and rel_path in _cache():
        return _cache()[rel_path]
    service = _service()
    found, _ = _locate_file(service, rel_path)
    if not found:
        return None
    meta = service.files().get(fileId=found["id"], fields="id,modifiedTime,version").execute()
    _versions()[rel_path] = str(meta.get("version") or meta.get("modifiedTime") or "")
    buf = io.BytesIO()
    req = service.files().get_media(fileId=found["id"])
    downloader = MediaIoBaseDownload(buf, req)
    done = False
    while not done:
        _, done = downloader.next_chunk()
    value = buf.getvalue()
    _cache()[rel_path] = value
    return value


def write_bytes(rel_path: str, value: bytes, mime_type: str = "application/octet-stream") -> bool:
    rel_path = str(PurePosixPath(rel_path))
    value = bytes(value)
    if not connected():
        st.session_state.setdefault("_gdrive_guest_files", {})[rel_path] = value
        return True
    _cache()[rel_path] = value
    _pending()[rel_path] = (value, mime_type)
    try:
        _upload_pending_one(rel_path)
        return True
    except Exception as exc:
        st.session_state["_gdrive_sync_error"] = str(exc)
        return False


def _execute_resumable(request):
    response = None
    while response is None:
        _, response = request.next_chunk()
    return response


def _upload_pending_one(rel_path: str):
    item = _pending().get(rel_path)
    if item is None:
        return
    value, mime_type = item
    service = _service()
    found, parent = _locate_file(service, rel_path)
    media = MediaIoBaseUpload(
        io.BytesIO(value), mimetype=mime_type, chunksize=5 * 1024 * 1024, resumable=True
    )
    if found:
        current = service.files().get(fileId=found["id"], fields="id,modifiedTime,version").execute()
        current_version = str(current.get("version") or current.get("modifiedTime") or "")
        expected = _versions().get(rel_path)
        if expected and current_version and current_version != expected:
            raise RuntimeError("Data Google Drive telah berubah di perangkat lain. Tekan Sinkronkan sekarang sebelum menyimpan kembali.")
        updated = _execute_resumable(service.files().update(
            fileId=found["id"], media_body=media, fields="id,modifiedTime,version"
        ))
        file_id = found["id"]
        _versions()[rel_path] = str(updated.get("version") or updated.get("modifiedTime") or current_version)
    else:
        created = _execute_resumable(service.files().create(
            body={"name": PurePosixPath(rel_path).name, "parents": [parent]},
            media_body=media,
            fields="id,modifiedTime,version",
        ))
        file_id = created["id"]
        _versions()[rel_path] = str(created.get("version") or created.get("modifiedTime") or "")
    _ids()[f"file:{rel_path}"] = file_id
    _pending().pop(rel_path, None)


def flush_pending(show_error: bool = False) -> bool:
    if not connected():
        return True
    ok = True
    for rel_path in list(_pending()):
        try:
            _upload_pending_one(rel_path)
        except Exception as exc:
            ok = False
            st.session_state["_gdrive_sync_error"] = str(exc)
    if show_error and not ok:
        st.error("Sebagian data belum berhasil disinkronkan ke Google Drive. Jangan tutup aplikasi sebelum sinkronisasi berhasil.")
    return ok


def exists(rel_path: str) -> bool:
    rel_path = str(PurePosixPath(rel_path))
    if not connected():
        return rel_path in st.session_state.setdefault("_gdrive_guest_files", {})
    if rel_path in _cache() or rel_path in _pending():
        return True
    try:
        service = _service()
        found, _ = _locate_file(service, rel_path)
        return bool(found)
    except Exception:
        return False


def delete(rel_path: str) -> bool:
    rel_path = str(PurePosixPath(rel_path))
    _cache().pop(rel_path, None)
    _pending().pop(rel_path, None)
    if not connected():
        st.session_state.setdefault("_gdrive_guest_files", {}).pop(rel_path, None)
        return True
    service = _service()
    found, _ = _locate_file(service, rel_path)
    if found:
        service.files().delete(fileId=found["id"]).execute()
    _ids().pop(f"file:{rel_path}", None)
    return True


def read_json(rel_path: str):
    raw = read_bytes(rel_path)
    if raw is None:
        return None
    return json.loads(raw.decode("utf-8"))


def write_json(rel_path: str, value) -> bool:
    payload = json.dumps(value, ensure_ascii=False, indent=2).encode("utf-8")
    return write_bytes(rel_path, payload, "application/json")


class RemotePath:
    """Small pathlib-compatible facade for existing D-Safe draft routines."""
    def __init__(self, rel_path: str):
        self.rel_path = str(PurePosixPath(rel_path))
    def __repr__(self):
        return f"RemotePath({self.rel_path!r})"
    def __hash__(self):
        return hash(self.rel_path)
    def __eq__(self, other):
        return isinstance(other, RemotePath) and self.rel_path == other.rel_path
    @property
    def name(self):
        return PurePosixPath(self.rel_path).name
    @property
    def suffix(self):
        return PurePosixPath(self.rel_path).suffix
    def exists(self):
        return exists(self.rel_path)
    def is_file(self):
        return self.exists()
    def read_bytes(self):
        value = read_bytes(self.rel_path)
        if value is None:
            raise FileNotFoundError(self.rel_path)
        return value
    def read_text(self, encoding="utf-8"):
        return self.read_bytes().decode(encoding)
    def write_bytes(self, value):
        write_bytes(self.rel_path, bytes(value))
        return len(value)
    def write_text(self, value, encoding="utf-8"):
        data = str(value).encode(encoding)
        mime = "application/json" if self.suffix == ".json" else "text/plain"
        write_bytes(self.rel_path, data, mime)
        return len(value)
    def unlink(self, missing_ok=False):
        if self.exists():
            delete(self.rel_path)
        elif not missing_ok:
            raise FileNotFoundError(self.rel_path)
    def with_suffix(self, suffix):
        return RemotePath(str(PurePosixPath(self.rel_path).with_suffix(suffix)))
    def replace(self, target):
        target = target if isinstance(target, RemotePath) else RemotePath(str(target))
        payload = self.read_bytes()
        target.write_bytes(payload)
        if target != self:
            self.unlink(missing_ok=True)
        return target


def handle_oauth_callback() -> bool:
    """Process a Google OAuth callback before normal page routing."""
    if not cloud_enabled() or not _libs_available():
        return False
    try:
        code = st.query_params.get("code")
        state = st.query_params.get("state")
    except Exception:
        return False
    if not code:
        return False
    if not state or not _valid_state(str(state)):
        st.session_state["_gdrive_auth_error"] = "Login Google ditolak karena state OAuth tidak valid atau kedaluwarsa. Silakan hubungkan kembali."
    else:
        try:
            flow = Flow.from_client_config(_client_config(), scopes=SCOPES, state=str(state), autogenerate_code_verifier=False)
            flow.redirect_uri = str(_cfg()["redirect_uri"])

            # Google may canonicalize the short OIDC aliases ``email``/``profile``
            # to their full userinfo scope URLs in the token response. OAuthLib
            # treats that standards-compliant representation change as a scope
            # mismatch unless its strict comparison is relaxed for this exchange.
            # We still verify the Drive permission explicitly immediately after.
            previous_relax_scope = os.environ.get("OAUTHLIB_RELAX_TOKEN_SCOPE")
            os.environ["OAUTHLIB_RELAX_TOKEN_SCOPE"] = "1"
            try:
                flow.fetch_token(code=str(code))
            finally:
                if previous_relax_scope is None:
                    os.environ.pop("OAUTHLIB_RELAX_TOKEN_SCOPE", None)
                else:
                    os.environ["OAUTHLIB_RELAX_TOKEN_SCOPE"] = previous_relax_scope

            creds = flow.credentials
            granted_scopes = set(creds.scopes or [])
            if "https://www.googleapis.com/auth/drive.file" not in granted_scopes:
                raise RuntimeError("Izin drive.file tidak diberikan oleh Google. Silakan hubungkan ulang dan setujui akses Google Drive.")
            st.session_state["_gdrive_credentials"] = _serialize_credentials(creds)
            st.session_state.pop("_gdrive_auth_error", None)
            st.session_state.pop("_gdrive_sync_error", None)
            # Resolve identity and initialize the root folder now.
            service = _service()
            about = service.about().get(fields="user(displayName,emailAddress,photoLink)").execute().get("user", {})
            st.session_state["_gdrive_user"] = about
            _ensure_path_folders(service, [])
            st.session_state["_gdrive_just_connected"] = True
        except Exception as exc:
            st.session_state["_gdrive_auth_error"] = f"Login Google Drive belum berhasil: {exc}"
    # Never leave OAuth authorization codes in the browser URL.
    try:
        for key in ("code", "state", "scope", "authuser", "prompt", "hd"):
            if key in st.query_params:
                del st.query_params[key]
        st.query_params["nav"] = "Pengaturan"
    except Exception:
        pass
    st.rerun()
    return True


def user_info() -> dict:
    if not connected():
        return {}
    info = st.session_state.get("_gdrive_user")
    if info:
        return info
    try:
        info = _service().about().get(fields="user(displayName,emailAddress,photoLink)").execute().get("user", {})
        st.session_state["_gdrive_user"] = info
        return info
    except Exception:
        return {}


def disconnect() -> bool:
    if _pending() and not flush_pending():
        return False
    for key in list(st.session_state):
        if key.startswith("_gdrive_"):
            del st.session_state[key]
    return True


def force_refresh_cache(*, discard_pending: bool = False):
    if _pending() and not discard_pending and not flush_pending():
        return False
    if discard_pending:
        st.session_state.pop("_gdrive_pending", None)
    st.session_state.pop("_gdrive_bytes_cache", None)
    st.session_state.pop("_gdrive_file_ids", None)
    st.session_state.pop("_gdrive_versions", None)
    st.session_state.pop("_gdrive_root_id", None)
    return True


def render_account_settings():
    if not cloud_enabled():
        st.info("Google Drive belum dikonfigurasi pada server aplikasi. Tambahkan konfigurasi Google OAuth pada Streamlit Secrets.")
        return
    if not _libs_available():
        st.error("Paket Google API belum terpasang. Jalankan instalasi dari requirements.txt versi Google Drive.")
        return
    error = st.session_state.pop("_gdrive_auth_error", None)
    if error:
        st.error(error)
    sync_error = st.session_state.get("_gdrive_sync_error")
    if sync_error:
        st.warning("Ada data yang belum tersinkron ke Google Drive. Gunakan Sinkronkan sekarang sebelum menutup aplikasi.")
    if connected():
        info = user_info()
        email = info.get("emailAddress") or "Akun Google terhubung"
        name = info.get("displayName") or ""
        st.success(f"Google Drive terhubung: {name + ' · ' if name else ''}{email}")
        st.caption("Data D-Safe tersimpan pada folder D-Safe milik akun ini. Aplikasi hanya meminta akses ke file yang dibuat/digunakan D-Safe.")
        c1, c2 = st.columns(2)
        if c1.button("↻ Sinkronkan sekarang", key="gdrive_sync_now_v1", use_container_width=True):
            if flush_pending(show_error=True) and force_refresh_cache():
                st.session_state.pop("_gdrive_sync_error", None)
                st.success("Sinkronisasi Google Drive selesai.")
                st.rerun()
        if c2.button("Putuskan akun", key="gdrive_disconnect_v1", use_container_width=True):
            if disconnect():
                st.rerun()
            else:
                st.error("Akun belum diputus karena masih ada data yang belum tersinkron.")
        if sync_error and "berubah di perangkat lain" in str(sync_error):
            st.warning("Versi Drive lebih baru. Gunakan tombol berikut hanya bila Anda ingin membuang perubahan lokal yang belum tersimpan dan memuat versi Drive terbaru.")
            if st.button("Muat versi terbaru dari Drive", key="gdrive_accept_remote_v1", use_container_width=True):
                force_refresh_cache(discard_pending=True)
                st.session_state.pop("_gdrive_sync_error", None)
                st.session_state.pop("_dsafe_guest_book", None)
                st.rerun()
    else:
        st.warning("Belum terhubung. Data yang dimasukkan sebelum login hanya tersimpan sementara pada sesi ini.")
        url = authorization_url()
        if url:
            st.link_button("Hubungkan Google Drive", url, use_container_width=True)
    admin_email = str(_cfg().get("admin_email") or "").strip()
    if admin_email:
        st.caption(f"Tujuan pengiriman PPT Admin: {admin_email}. Admin hanya menerima salinan PPT yang Anda kirim.")
    else:
        st.caption("Email Admin belum dikonfigurasi; tombol Kirim ke Admin akan dinonaktifkan.")


def _period_parts(filename: str):
    months = ["Januari","Februari","Maret","April","Mei","Juni","Juli","Agustus","September","Oktober","November","Desember"]
    numeric = re.search(r"\b(\d{2})-(\d{2})-(20\d{2}|21\d{2})\b", filename)
    if numeric:
        month_no = int(numeric.group(2))
        if 1 <= month_no <= 12:
            return numeric.group(3), months[month_no - 1]
    year_match = re.search(r"\b(20\d{2}|21\d{2})\b", filename)
    year = year_match.group(1) if year_match else datetime.now().strftime("%Y")
    month = next((m for m in months if re.search(re.escape(m), filename, flags=re.I)), None)
    if month is None:
        month = months[datetime.now(timezone(timedelta(hours=7))).month - 1]
    return year, month


def _category_folder(category: str) -> str:
    return {
        "book": "Output Buku Kerja",
        "dsafe": "Output D-Safe",
        "safety": "Output Safety Talk",
    }.get(category, "Output")


def save_output(data: bytes, filename: str, mime_type: str, category: str) -> str:
    if not connected():
        raise RuntimeError("Hubungkan Google Drive terlebih dahulu melalui Pengaturan.")
    year, month = _period_parts(filename)
    rel = f"{_category_folder(category)}/{year}/{month}/{filename}"
    if not write_bytes(rel, data, mime_type):
        raise RuntimeError(st.session_state.get("_gdrive_sync_error") or "Gagal menyimpan output ke Google Drive.")
    return rel


def _next_admin_filename(service, parent_id: str, filename: str) -> str:
    stem, dot, ext = filename.rpartition(".")
    if not dot:
        stem, ext = filename, ""
    candidate = filename
    if not _find_child(service, parent_id, candidate):
        return candidate
    for n in range(2, 1000):
        candidate = f"{stem} - R{n}.{ext}" if ext else f"{stem} - R{n}"
        if not _find_child(service, parent_id, candidate):
            return candidate
    stamp = datetime.now(timezone(timedelta(hours=7))).strftime("%Y%m%d-%H%M%S")
    return f"{stem} - {stamp}.{ext}" if ext else f"{stem} - {stamp}"


def send_to_admin(data: bytes, filename: str, mime_type: str, category: str) -> str:
    if not connected():
        raise RuntimeError("Hubungkan Google Drive terlebih dahulu melalui Pengaturan.")
    admin_email = str(_cfg().get("admin_email") or "").strip()
    if not admin_email:
        raise RuntimeError("Email Admin belum dikonfigurasi.")
    service = _service()
    year, month = _period_parts(filename)
    parent = _ensure_path_folders(service, ["Terkirim ke Admin", year, month])
    admin_name = _next_admin_filename(service, parent, filename)
    media = MediaIoBaseUpload(
        io.BytesIO(bytes(data)), mimetype=mime_type, chunksize=5 * 1024 * 1024, resumable=True
    )
    created = _execute_resumable(service.files().create(
        body={"name": admin_name, "parents": [parent]},
        media_body=media,
        fields="id,name",
    ))
    notify = bool(_cfg().get("admin_notify", False))
    service.permissions().create(
        fileId=created["id"],
        body={"type": "user", "role": "reader", "emailAddress": admin_email},
        sendNotificationEmail=notify,
        fields="id",
    ).execute()
    return created.get("name") or admin_name


def render_output_actions(data: bytes, filename: str, mime_type: str, category: str, *, allow_admin: bool = False):
    """Add Drive actions below an existing D-Safe download button."""
    if not cloud_enabled() or not data:
        return
    digest = hashlib.sha1((filename + str(len(data))).encode("utf-8")).hexdigest()[:12]
    if not connected():
        st.caption("Hubungkan Google Drive di Pengaturan untuk menyimpan output" + (" dan mengirim PPT ke Admin." if allow_admin else "."))
        return
    result_key = f"_gdrive_output_result_{digest}"
    prior = st.session_state.pop(result_key, None)
    if prior:
        kind, message = prior
        (st.success if kind == "ok" else st.error)(message)
    cols = st.columns(2 if allow_admin else 1)
    if cols[0].button("☁ Simpan ke Drive Saya", key=f"gdrive_save_{digest}", use_container_width=True):
        try:
            save_output(data, filename, mime_type, category)
            st.session_state[result_key] = ("ok", "Output berhasil disimpan ke Google Drive Anda.")
        except Exception as exc:
            st.session_state[result_key] = ("error", f"Penyimpanan ke Google Drive gagal: {exc}")
        st.rerun()
    if allow_admin:
        disabled = not admin_configured()
        if cols[1].button("⇧ Kirim ke Admin", key=f"gdrive_admin_{digest}", use_container_width=True, disabled=disabled):
            try:
                sent_name = send_to_admin(data, filename, mime_type, category)
                st.session_state[result_key] = ("ok", f"PPT berhasil dikirim ke Admin sebagai {sent_name}.")
            except Exception as exc:
                st.session_state[result_key] = ("error", f"Pengiriman ke Admin gagal: {exc}")
            st.rerun()


def save_backup_archive(data: bytes, filename: str) -> bool:
    if not connected():
        return False
    return write_bytes(f"Cadangan/{filename}", data, "application/zip")


def clear_app_session_state_preserve_auth():
    """Clear D-Safe widget state without dropping the connected Google account."""
    preserved = {k: v for k, v in st.session_state.items() if str(k).startswith("_gdrive_")}
    st.session_state.clear()
    for key, value in preserved.items():
        st.session_state[key] = value
