import base64
import ctypes
from ctypes import wintypes


class DATA_BLOB(ctypes.Structure):
    _fields_ = [
        ("cbData", wintypes.DWORD),
        ("pbData", ctypes.POINTER(ctypes.c_byte)),
    ]


def _bytes_to_blob(data: bytes) -> DATA_BLOB:
    buf = (ctypes.c_byte * len(data)).from_buffer_copy(data)
    return DATA_BLOB(cbData=len(data), pbData=ctypes.cast(buf, ctypes.POINTER(ctypes.c_byte)))


def _blob_to_bytes(blob: DATA_BLOB) -> bytes:
    if not blob.pbData:
        return b""
    return ctypes.string_at(blob.pbData, blob.cbData)


def protect_to_b64(plaintext: str) -> str:
    """Encrypt plaintext using Windows DPAPI (user scope) and return base64 string."""
    if plaintext is None:
        plaintext = ""
    data = plaintext.encode("utf-8")

    in_blob = _bytes_to_blob(data)
    out_blob = DATA_BLOB()

    crypt32 = ctypes.windll.crypt32
    kernel32 = ctypes.windll.kernel32

    # BOOL CryptProtectData(DATA_BLOB*, LPCWSTR, DATA_BLOB*, PVOID, PVOID, DWORD, DATA_BLOB*)
    CRYPTPROTECT_UI_FORBIDDEN = 0x1
    ok = crypt32.CryptProtectData(
        ctypes.byref(in_blob),
        None,
        None,
        None,
        None,
        CRYPTPROTECT_UI_FORBIDDEN,
        ctypes.byref(out_blob),
    )
    if not ok:
        raise OSError("CryptProtectData failed")

    try:
        protected = _blob_to_bytes(out_blob)
        return base64.b64encode(protected).decode("ascii")
    finally:
        try:
            kernel32.LocalFree(out_blob.pbData)
        except Exception:
            pass


def unprotect_from_b64(b64_ciphertext: str) -> str:
    """Decrypt base64 DPAPI ciphertext back to UTF-8 plaintext."""
    if not b64_ciphertext:
        return ""
    raw = base64.b64decode(b64_ciphertext)

    in_blob = _bytes_to_blob(raw)
    out_blob = DATA_BLOB()

    crypt32 = ctypes.windll.crypt32
    kernel32 = ctypes.windll.kernel32

    CRYPTPROTECT_UI_FORBIDDEN = 0x1
    ok = crypt32.CryptUnprotectData(
        ctypes.byref(in_blob),
        None,
        None,
        None,
        None,
        CRYPTPROTECT_UI_FORBIDDEN,
        ctypes.byref(out_blob),
    )
    if not ok:
        raise OSError("CryptUnprotectData failed")

    try:
        data = _blob_to_bytes(out_blob)
        return data.decode("utf-8", errors="replace")
    finally:
        try:
            kernel32.LocalFree(out_blob.pbData)
        except Exception:
            pass


