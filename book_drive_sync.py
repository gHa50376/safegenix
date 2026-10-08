"""Per-account Buku Kerja persistence and safe merging across browser sessions."""

from copy import deepcopy
import json

try:
    from streamlit.runtime.scriptrunner import get_script_run_ctx
except ImportError:
    get_script_run_ctx = None


BOOK_PATH = "Data/buku_kerja_v341.json"
_MISSING = object()


class BookConflict(RuntimeError):
    pass


def _resolve(base, local, remote):
    if local == base or local == remote:
        return remote
    if remote == base:
        return local
    raise BookConflict(
        "Data yang sama telah diubah di perangkat lain. Perubahan Anda belum "
        "disimpan; data Drive tetap dipertahankan."
    )


def _merge_records(base, local, remote, key):
    def index(rows):
        result = {}
        for row in rows or []:
            identifier = str(key(row) or "")
            if not identifier or identifier in result:
                raise BookConflict("Identitas data tidak valid; penyimpanan dibatalkan.")
            result[identifier] = row
        return result

    before, desired, latest = map(index, (base, local, remote))
    merged = []
    for identifier in dict.fromkeys([*latest, *desired, *before]):
        value = _resolve(before.get(identifier, _MISSING),
                         desired.get(identifier, _MISSING),
                         latest.get(identifier, _MISSING))
        if value is not _MISSING:
            merged.append(deepcopy(value))
    return merged


def merge_book_changes(base, local, remote):
    """Apply this device's changes, retaining other-device additions/deletions."""
    result = deepcopy(remote)
    for key in set(base) | set(local) | set(remote):
        if key in ("sessions", "people", "activities"):
            continue
        value = _resolve(base.get(key, _MISSING), local.get(key, _MISSING),
                         remote.get(key, _MISSING))
        if value is _MISSING:
            result.pop(key, None)
        else:
            result[key] = deepcopy(value)

    result["people"] = _merge_records(
        base.get("people"), local.get("people"), remote.get("people"),
        lambda row: row.get("key") or row.get("short") or row.get("nipp"))
    result["activities"] = _merge_records(
        base.get("activities"), local.get("activities"), remote.get("activities"),
        lambda row: row.get("id"))

    def sessions(book):
        return [dict(row, activityId=str(aid))
                for aid, rows in (book.get("sessions") or {}).items() for row in rows]

    rows = _merge_records(sessions(base), sessions(local), sessions(remote),
                          lambda row: row.get("id"))
    result["sessions"] = {}
    for row in rows:
        result["sessions"].setdefault(row["activityId"], []).append(row)
    return result


class DriveBookStore:
    """Only acknowledged Drive writes become the saved baseline."""

    def __init__(self, drive, state, normalize, default):
        self.drive, self.state = drive, state
        self.normalize, self.default = normalize, default

    def _owner(self):
        email = str((self.drive.user_info() or {}).get("emailAddress") or "").strip().lower()
        if not email:
            raise RuntimeError("Identitas akun Google belum dapat dibaca. Coba masuk kembali.")
        previous = self.state.get("_gdrive_book_owner")
        if previous and previous != email:
            if self.state.get("_gdrive_book_unsaved"):
                raise RuntimeError("Selesaikan penyimpanan pada akun sebelumnya sebelum mengganti akun.")
            self.drive.force_refresh_cache(discard_pending=True)
            for key in list(self.state):
                if str(key).startswith("_gdrive_book_") or key == "_dsafe_guest_book":
                    self.state.pop(key, None)
        self.state["_gdrive_book_owner"] = email

    def _read(self, force=False):
        raw = self.drive.read_json(BOOK_PATH, refresh=force, refresh_if_changed=True)
        if raw is not None and not isinstance(raw, dict):
            raise RuntimeError("Format Buku Kerja di Drive tidak valid; data tidak ditimpa.")
        return self.normalize(deepcopy(raw if raw is not None else self.default)), raw

    def _remember(self, data):
        self.state["_gdrive_book_baseline"] = deepcopy(data)
        self.state["_dsafe_guest_book"] = deepcopy(data)

    def _commit(self, remote, target, raw):
        self.state["_gdrive_book_unsaved"] = deepcopy(target)
        self.state["_gdrive_book_baseline"] = deepcopy(remote)
        self.state["_dsafe_guest_book"] = deepcopy(target)
        if raw != target and not self.drive.write_json(BOOK_PATH, target):
            # The book retries through this store, never as a stale full-file
            # upload in the generic queue for reports/drafts.
            self.state.get("_gdrive_pending", {}).pop(BOOK_PATH, None)
            raise RuntimeError(self.state.get("_gdrive_sync_error") or
                               "Data belum berhasil tersimpan di Google Drive.")
        self.state.get("_gdrive_pending", {}).pop(BOOK_PATH, None)
        self.state.pop("_gdrive_book_unsaved", None)
        self.state.pop("_gdrive_book_error", None)
        self._remember(target)
        return deepcopy(target)

    def load(self, *, refresh=False):
        self._owner()
        marker = None
        if get_script_run_ctx is not None:
            try:
                marker = getattr(get_script_run_ctx(suppress_warning=True),
                                 "widget_ids_this_run", None)
            except Exception:
                pass
        if (not refresh and marker is not None and
                self.state.get("_gdrive_book_read_run") is marker and
                not self.state.get("_gdrive_book_unsaved")):
            return deepcopy(self.state["_gdrive_book_baseline"])

        # Older in-flight writes retain their original revision guard.
        if not self.drive.flush_pending() and BOOK_PATH in self.state.get("_gdrive_pending", {}):
            raise RuntimeError("Penyimpanan kegiatan sebelumnya belum selesai. Coba lagi.")
        local = self.state.get("_gdrive_book_unsaved")
        remote, raw = self._read(force=bool(local))
        if local is not None:
            base = self.state.get("_gdrive_book_baseline", remote)
            target = merge_book_changes(base, local, remote)
        else:
            target = deepcopy(remote)
        if "storage_state" not in target:
            # Existing reset archives keep recovery available after upgrading.
            archives = self.drive.list_reset_backup_archives() if raw is not None else []
            target["storage_state"] = {"has_reset": bool(archives)}
        data = self._commit(remote, target, raw)
        if local is not None:
            self.state["_gdrive_book_recovered"] = True
        if marker is not None:
            self.state["_gdrive_book_read_run"] = marker
        self.state.pop("_gdrive_just_connected", None)
        return data

    def save(self, data):
        self._owner()
        desired = self.normalize(deepcopy(data))
        base = self.state.get("_gdrive_book_baseline")
        if base is None:
            raise RuntimeError("Muat Buku Kerja dari Drive sebelum menyimpan kegiatan.")
        retry = bool(self.state.get("_gdrive_book_unsaved") or
                     self.state.get("_gdrive_book_error"))
        try:
            remote, raw = self._read(force=retry)
        finally:
            self.state["_gdrive_book_unsaved"] = deepcopy(desired)
            self.state["_dsafe_guest_book"] = deepcopy(desired)
        target = merge_book_changes(base, desired, remote)
        return self._commit(remote, target, raw)


def reset_state(data, *, archive, start, end, count, timestamp):
    """Persist recovery availability with the reset's active-book write."""
    state = deepcopy(data.get("storage_state") or {})
    state.update(has_reset=True, last_reset={
        "archive": archive, "start": start.isoformat(), "end": end.isoformat(),
        "count": count, "at": timestamp,
    })
    return state
