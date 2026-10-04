"""SAFEGENIX shared access registry gate.

Google OAuth proves identity. This module only decides whether that verified
Google account may open SAFEGENIX. Registry is stored in a GitHub JSON file so
the user app and SAFEGENIX Admin can share one source of truth.
"""
from __future__ import annotations

import base64
import json
from datetime import datetime, timezone, timedelta
from urllib import request, error
import streamlit as st

JAKARTA = timezone(timedelta(hours=7))


def _cfg():
    try:
        c = dict(st.secrets.get("access_registry", {}) or {})
    except Exception:
        c = {}
    # Safe project defaults; secrets may override all of these.
    c.setdefault("repo", "gHa50376/dsafe-penyimpanan-perangkat")
    c.setdefault("branch", "registry")
    c.setdefault("path", "authorized_users.json")
    return c


def _token():
    c = _cfg()
    for key in ("token", "github_token", "registry_token"):
        if c.get(key):
            return str(c[key]).strip()
    try:
        for key in ("GITHUB_TOKEN", "github_token", "registry_token"):
            if st.secrets.get(key):
                return str(st.secrets[key]).strip()
    except Exception:
        pass
    return ""


def _api(method="GET", payload=None):
    c = _cfg(); token = _token()
    if not token:
        raise RuntimeError("Token Registry SAFEGENIX belum dikonfigurasi di Streamlit Secrets.")
    url = f"https://api.github.com/repos/{c['repo']}/contents/{c['path']}?ref={c['branch']}"
    headers = {
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {token}",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "SAFEGENIX-access-registry",
    }
    data = None if payload is None else json.dumps(payload).encode("utf-8")
    req = request.Request(url, data=data, headers=headers, method=method)
    try:
        with request.urlopen(req, timeout=15) as r:
            return json.loads(r.read().decode("utf-8"))
    except error.HTTPError as exc:
        detail = exc.read().decode("utf-8", "replace")
        raise RuntimeError(f"Registry SAFEGENIX tidak dapat diakses ({exc.code}): {detail[:240]}") from exc
    except Exception as exc:
        raise RuntimeError(f"Registry SAFEGENIX tidak dapat diakses: {exc}") from exc


def _normalize(raw):
    """Accept legacy list or {'users': [...]} registries; return canonical dict."""
    if isinstance(raw, list):
        return {"version": 2, "users": raw}
    if not isinstance(raw, dict):
        return {"version": 2, "users": []}
    out = dict(raw)
    users = out.get("users")
    if isinstance(users, dict):
        rows=[]
        for email, value in users.items():
            row = dict(value) if isinstance(value, dict) else {}
            row.setdefault("email", email); rows.append(row)
        out["users"] = rows
    elif not isinstance(users, list):
        # Compatibility with registries whose top-level values are email records.
        rows=[]
        for k,v in raw.items():
            if "@" in str(k) and isinstance(v, dict):
                row=dict(v); row.setdefault("email",k); rows.append(row)
        out["users"] = rows
    out.setdefault("version", 2)
    out.setdefault("users", [])
    return out


def read_registry():
    meta = _api()
    content = base64.b64decode(meta.get("content", "")).decode("utf-8-sig")
    raw = json.loads(content) if content.strip() else {}
    return _normalize(raw), meta.get("sha")


def _write_registry(registry, sha, message):
    c=_cfg()
    body={
        "message": message,
        "content": base64.b64encode(json.dumps(registry,ensure_ascii=False,indent=2).encode("utf-8")).decode("ascii"),
        "branch": c["branch"],
    }
    if sha: body["sha"] = sha
    return _api("PUT", body)


def _email(row):
    return str(row.get("email") or row.get("gmail") or row.get("user_email") or "").strip().lower()


def _status(row):
    value = str(row.get("status") or "").strip().upper()
    if value in {"ACTIVE","AKTIF","APPROVED","ALLOWED","ENABLED"}: return "ACTIVE"
    if value in {"DISABLED","NONAKTIF","INACTIVE","BLOCKED","REJECTED","DENIED"}: return "DISABLED"
    if value in {"PENDING","MENUNGGU","REQUESTED"}: return "PENDING"
    # Legacy admin rows often use an active/enabled boolean.
    if row.get("active") is True or row.get("enabled") is True: return "ACTIVE"
    if row.get("active") is False or row.get("enabled") is False: return "DISABLED"
    return "PENDING"


def get_user(email):
    registry,_ = read_registry(); target=str(email).strip().lower()
    for row in registry["users"]:
        if isinstance(row,dict) and _email(row)==target:
            return row, _status(row)
    return None, "MISSING"


def ensure_pending(email, name="", photo=""):
    """Create one pending request. Existing Admin decisions are never overwritten."""
    target=str(email).strip().lower()
    for attempt in range(2):
        registry,sha = read_registry()
        for row in registry["users"]:
            if isinstance(row,dict) and _email(row)==target:
                return row, _status(row)
        now=datetime.now(JAKARTA).isoformat(timespec="seconds")
        row={
            "email": target,
            "name": str(name or "").strip(),
            "station": "",
            "note": "Permintaan akses otomatis dari aplikasi SAFEGENIX",
            "status": "PENDING",
            "active": False,
            "requested_at": now,
            "photo": str(photo or ""),
        }
        registry["users"].append(row)
        registry["updated_at"] = now
        try:
            _write_registry(registry,sha,f"SAFEGENIX access request: {target}")
            return row,"PENDING"
        except RuntimeError as exc:
            if attempt == 0 and "409" in str(exc):
                continue
            raise
    return row,"PENDING"


def _locked_card(title, message, kind="info"):
    st.markdown("""
    <style>
    .block-container{max-width:720px;padding-top:8vh!important}
    .sg-access-card{padding:28px 24px;border:1px solid #d4e5f5;border-radius:24px;background:#fff;
      box-shadow:0 18px 55px rgba(28,78,125,.12);text-align:center;margin-bottom:16px}
    .sg-access-logo{font-size:1.55rem;font-weight:950;letter-spacing:.18em;color:#145fb7;margin-bottom:8px}
    .sg-access-title{font-size:1.15rem;font-weight:850;color:#173f70;margin-bottom:8px}
    .sg-access-copy{font-size:.9rem;line-height:1.55;color:#607b94}
    </style>""", unsafe_allow_html=True)
    st.markdown(f"<div class='sg-access-card'><div class='sg-access-logo'>SAFEGENIX</div><div class='sg-access-title'>{title}</div><div class='sg-access-copy'>{message}</div></div>",unsafe_allow_html=True)


def require_approved_user(gdrive):
    """Stop Streamlit unless the connected, Google-verified email is ACTIVE."""
    info=gdrive.user_info() or {}
    email=str(info.get("emailAddress") or "").strip().lower()
    name=str(info.get("displayName") or "").strip()
    photo=str(info.get("photoLink") or "")
    if not email:
        _locked_card("Identitas Google belum tersedia","Putuskan akun lalu masuk kembali dengan akun Google yang akan digunakan.")
        if st.button("Keluar dari akun Google",use_container_width=True):
            if gdrive.disconnect(): st.rerun()
        st.stop()
    try:
        row,status=get_user(email)
        if status=="MISSING":
            row,status=ensure_pending(email,name,photo)
    except Exception as exc:
        _locked_card("Registry belum dapat diperiksa", "SAFEGENIX tetap terkunci agar akses tidak terbuka tanpa persetujuan Admin.")
        st.error(str(exc))
        if st.button("Coba lagi",use_container_width=True): st.rerun()
        st.stop()

    if status=="ACTIVE":
        st.session_state["_safegenix_access_email"] = email
        return

    if status=="DISABLED":
        _locked_card("Akses SAFEGENIX tidak aktif",f"Akun <b>{email}</b> sudah teridentifikasi, tetapi aksesnya sedang dinonaktifkan oleh Admin.")
    else:
        _locked_card("Menunggu persetujuan Admin",f"Permintaan akses untuk <b>{email}</b> sudah tercatat. Setelah Admin menekan <b>Izinkan</b>, tekan tombol cek status di bawah.")
    c1,c2=st.columns(2)
    if c1.button("↻ Cek Status",use_container_width=True): st.rerun()
    if c2.button("Ganti Akun Google",use_container_width=True):
        if gdrive.disconnect(): st.rerun()
    st.stop()


def submit_access_profile(email: str, name: str, station: str, photo: str = ""):
    """Create/update the user's identity without allowing the user app to self-approve."""
    target = str(email or "").strip().lower()
    name = str(name or "").strip()
    station = str(station or "").strip()
    if not target or not name or not station:
        raise ValueError("Email Google, Nama Pengguna, dan Nama Stasiun wajib tersedia.")
    for attempt in range(2):
        registry, sha = read_registry()
        now = datetime.now(JAKARTA).isoformat(timespec="seconds")
        found = None
        for row in registry.get("users", []):
            if isinstance(row, dict) and _email(row) == target:
                found = row
                break
        if found is None:
            found = {
                "email": target,
                "status": "PENDING",
                "active": False,
                "requested_at": now,
                "note": "Permintaan akses dari Pengaturan SAFEGENIX",
            }
            registry.setdefault("users", []).append(found)
        # Identity may be updated by the user, but an Admin decision is preserved.
        found["name"] = name
        found["station"] = station
        found["photo"] = str(photo or found.get("photo") or "")
        found["updated_at"] = now
        if _status(found) == "PENDING" and not found.get("requested_at"):
            found["requested_at"] = now
        registry["updated_at"] = now
        try:
            _write_registry(registry, sha, f"SAFEGENIX profile/access request: {target}")
            verified, status = get_user(target)
            if verified is None or _email(verified) != target:
                raise RuntimeError("Permintaan akses belum ditemukan saat Registry diperiksa kembali.")
            if str(verified.get("name") or "").strip() != name or str(verified.get("station") or "").strip() != station:
                raise RuntimeError("Identitas di Registry berubah. Silakan simpan kembali.")
            return verified, status
        except RuntimeError as exc:
            if attempt == 0 and "409" in str(exc):
                continue
            raise
    return found, _status(found)
