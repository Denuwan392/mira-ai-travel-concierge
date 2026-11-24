"""Read validated source snapshots through SQLite before requesting a price."""
from hashlib import sha256
from xml.etree.ElementTree import ParseError
from zipfile import BadZipFile

from . import data
from .data import Unavailable
from .store import db


def current_rates():
    try:
        workbook = data.WORKBOOK.read_bytes()
        checksum = sha256(workbook).hexdigest()
        with db() as conn:
            stored = conn.execute("SELECT workbook FROM rate_snapshots WHERE digest=?", (checksum,)).fetchone()
        if stored:
            return data.parse_rates(stored["workbook"])
        rates = data.parse_rates(workbook)
        with db() as conn:
            conn.execute("INSERT OR IGNORE INTO rate_snapshots(digest, workbook) VALUES (?,?)", (checksum, workbook))
        return rates
    except Unavailable:
        raise
    except (OSError, BadZipFile, ParseError, AttributeError, TypeError, ValueError, KeyError, IndexError) as exc:
        raise Unavailable("rate_import_invalid") from exc
