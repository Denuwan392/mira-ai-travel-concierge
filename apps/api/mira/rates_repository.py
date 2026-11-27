"""Validated rate-sheet snapshot repository backed by SQLite.

Computes a SHA-256 digest of the Excel rate workbook, returns cached parsed
rates from ``rate_snapshots`` when available, or validates and persists new
snapshots before any pricing calculation runs.
"""
from hashlib import sha256
from xml.etree.ElementTree import ParseError
from zipfile import BadZipFile

from . import data
from .data import Unavailable
from .store import db


def current_rates():
    """Load, validate, and snapshot-cache the active Excel rate workbook.

    Returns:
        A ``data.Rates`` dataclass instance parsed from the current workbook.

    Raises:
        Unavailable: With ``"rate_import_invalid"`` if the workbook cannot be
            read or parsed (e.g., missing file, corrupt ZIP/XML, bad schema), or
            any ``Unavailable`` error raised by ``data.parse_rates``.
    """
    try:
        workbook = data.WORKBOOK.read_bytes()
        checksum = sha256(workbook).hexdigest()
        # Reuse the stored snapshot if this exact workbook digest is already recorded.
        with db() as conn:
            stored = conn.execute("SELECT workbook FROM rate_snapshots WHERE digest=?", (checksum,)).fetchone()
        if stored:
            return data.parse_rates(stored["workbook"])
        # Parse and validate before persisting so corrupt workbooks are never cached.
        rates = data.parse_rates(workbook)
        with db() as conn:
            conn.execute("INSERT OR IGNORE INTO rate_snapshots(digest, workbook) VALUES (?,?)", (checksum, workbook))
        return rates
    except Unavailable:
        raise
    except (OSError, BadZipFile, ParseError, AttributeError, TypeError, ValueError, KeyError, IndexError) as exc:
        raise Unavailable("rate_import_invalid") from exc
