#!/usr/bin/env python3
"""Repair wheel dist-info naming/RECORD for a local publish copy.

The GitHub release assets are treated as immutable. This rewrites only the
downloaded copy used for the PyPI upload so its dist-info directory matches
the normalized wheel filename and its RECORD is correct.
"""

from __future__ import annotations

import base64
import csv
import hashlib
import io
import re
import sys
import tempfile
import zipfile
from pathlib import Path


def normalize(name: str) -> str:
    return re.sub(r"[-_.]+", "_", name).lower()


def digest(data: bytes) -> str:
    value = base64.urlsafe_b64encode(hashlib.sha256(data).digest()).rstrip(b"=")
    return f"sha256={value.decode('ascii')}"


def main() -> None:
    path = Path(sys.argv[1])
    if not path.name.lower().endswith(".whl"):
        raise SystemExit(f"not a wheel: {path}")

    stem = path.name[:-4]
    parts = stem.split("-")
    if len(parts) < 5:
        raise SystemExit(f"invalid wheel filename: {path.name}")

    distribution = parts[0]
    version = parts[1]
    expected_dist_info = f"{normalize(distribution)}-{version}.dist-info"

    with zipfile.ZipFile(path, "r") as source:
        entries = [(info, source.read(info.filename)) for info in source.infolist()]

    metadata = [
        (info, data)
        for info, data in entries
        if info.filename.endswith(".dist-info/METADATA")
    ]
    if len(metadata) != 1:
        raise SystemExit(f"expected exactly one METADATA entry, found {len(metadata)}")

    metadata_info, metadata_data = metadata[0]
    actual_dist_info = metadata_info.filename.rsplit("/", 1)[0]
    actual_prefix = actual_dist_info + "/"
    expected_prefix = expected_dist_info + "/"

    rewritten: list[tuple[str, bytes, zipfile.ZipInfo]] = []
    wheel_found = False

    for info, data in entries:
        if info.filename.startswith(actual_prefix):
            name = expected_prefix + info.filename[len(actual_prefix):]
        else:
            name = info.filename

        if name == expected_prefix + "WHEEL":
            wheel_found = True

        if name == expected_prefix + "RECORD":
            continue

        if name == expected_prefix + "METADATA":
            data = metadata_data

        rewritten.append((name, data, info))

    if not wheel_found:
        tag = "-".join(parts[2:])
        wheel_text = (
            "Wheel-Version: 1.0\n"
            "Generator: ViciousSquid wheel repair\n"
            "Root-Is-Purelib: false\n"
            f"Tag: {tag}\n"
        ).encode("utf-8")
        info = zipfile.ZipInfo(expected_prefix + "WHEEL")
        info.compress_type = zipfile.ZIP_DEFLATED
        rewritten.append((expected_prefix + "WHEEL", wheel_text, info))
        print(f"Added missing {expected_prefix}WHEEL")

    record_rows: list[list[str]] = []
    for name, data, _ in rewritten:
        record_rows.append([name, digest(data), str(len(data))])
    record_rows.append([expected_prefix + "RECORD", "", ""])

    output = io.StringIO()
    csv.writer(output, lineterminator="\n").writerows(record_rows)
    record_data = output.getvalue().encode("utf-8")
    record_info = zipfile.ZipInfo(expected_prefix + "RECORD")

    with tempfile.NamedTemporaryFile(delete=False, suffix=".whl", dir=path.parent) as temp:
        temp_path = Path(temp.name)

    try:
        with zipfile.ZipFile(temp_path, "w") as destination:
            for name, data, original in rewritten:
                info = zipfile.ZipInfo(name, date_time=original.date_time)
                info.compress_type = original.compress_type
                info.external_attr = original.external_attr
                info.create_system = original.create_system
                info.comment = original.comment
                info.extra = original.extra
                destination.writestr(info, data)
            record_info.compress_type = zipfile.ZIP_DEFLATED
            destination.writestr(record_info, record_data)

        temp_path.replace(path)
    except Exception:
        temp_path.unlink(missing_ok=True)
        raise

    with zipfile.ZipFile(path, "r") as check:
        names = set(check.namelist())
        required = {expected_prefix + "METADATA", expected_prefix + "WHEEL", expected_prefix + "RECORD"}
        missing = required - names
        if missing:
            raise SystemExit(f"repair failed; missing: {sorted(missing)}")

    print(f"Prepared valid publish wheel: {path.name}")
    print(f"  dist-info: {expected_dist_info}")


if __name__ == "__main__":
    main()
