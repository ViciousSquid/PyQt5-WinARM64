#!/usr/bin/env python3
"""Retag a wheel distribution without changing its import package."""

from __future__ import annotations

import argparse
import base64
import csv
import hashlib
import io
import re
import tempfile
import zipfile
from pathlib import Path


def normalize_wheel_name(name: str) -> str:
    return re.sub(r"[-_.]+", "_", name).lower()


def wheel_filename(name: str, old_name: str, new_name: str) -> str:
    old_prefix = normalize_wheel_name(old_name) + "-"
    if not name.startswith(old_prefix) or not name.endswith(".whl"):
        raise ValueError(f"wheel filename does not start with {old_prefix!r}: {name}")
    return normalize_wheel_name(new_name) + name[len(normalize_wheel_name(old_name)) :]


def digest(data: bytes) -> str:
    encoded = base64.urlsafe_b64encode(hashlib.sha256(data).digest()).rstrip(b"=")
    return f"sha256={encoded.decode('ascii')}"


def rewrite_wheel(path: Path, old_name: str, new_name: str, requirements: list[tuple[str, str]]) -> Path:
    new_path = path.with_name(wheel_filename(path.name, old_name, new_name))

    with zipfile.ZipFile(path, "r") as source:
        entries: list[tuple[zipfile.ZipInfo, bytes]] = []
        metadata_name = None
        dist_info_prefix = None

        for info in source.infolist():
            data = source.read(info.filename)
            if info.filename.endswith(".dist-info/METADATA"):
                metadata_name = info.filename
                dist_info_prefix = info.filename.rsplit("/", 1)[0] + "/"
            entries.append((info, data))

    if metadata_name is None or dist_info_prefix is None:
        raise ValueError(f"no .dist-info/METADATA found in {path}")

    metadata = next(data for info, data in entries if info.filename == metadata_name).decode("utf-8")
    if not re.search(r"(?m)^Name:\s*" + re.escape(old_name) + r"\s*$", metadata, re.IGNORECASE):
        raise ValueError(f"wheel metadata does not declare Name: {old_name}")

    metadata = re.sub(
        r"(?m)^(Name:\s*)" + re.escape(old_name) + r"\s*$",
        r"\g<1>" + new_name,
        metadata,
        count=1,
        flags=re.IGNORECASE,
    )
    for old_requirement, new_requirement in requirements:
        metadata = re.sub(
            r"(?im)^(Requires-Dist:\s*)" + re.escape(old_requirement) + r"(?=\s*(?:[;(]|$))",
            r"\g<1>" + new_requirement,
            metadata,
        )

    old_dist_info = dist_info_prefix.rstrip("/")
    version = old_dist_info.rsplit("-", 1)[1].removesuffix(".dist-info")
    new_dist_info = f"{normalize_wheel_name(new_name)}-{version}.dist-info"

    rewritten: list[tuple[str, bytes, zipfile.ZipInfo]] = []
    for info, data in entries:
        name = info.filename
        if name.endswith(".dist-info/RECORD"):
            continue
        if name.startswith(old_dist_info + "/"):
            name = new_dist_info + name[len(old_dist_info) :]
        if name == new_dist_info + "/METADATA":
            data = metadata.encode("utf-8")
        rewritten.append((name, data, info))

    record_name = new_dist_info + "/RECORD"
    record_rows: list[list[str]] = []
    for name, data, _ in rewritten:
        record_rows.append([name, digest(data), str(len(data))])
    record_rows.append([record_name, "", ""])

    output = io.StringIO()
    csv.writer(output, lineterminator="\n").writerows(record_rows)
    record_text = output.getvalue().encode("utf-8")
    rewritten.append((record_name, record_text, zipfile.ZipInfo(record_name)))

    with tempfile.NamedTemporaryFile(delete=False, suffix=".whl", dir=path.parent) as temp:
        temp_path = Path(temp.name)

    try:
        with zipfile.ZipFile(temp_path, "w") as destination:
            for name, data, original in rewritten:
                if original.filename == record_name:
                    info = original
                else:
                    info = zipfile.ZipInfo(name, date_time=original.date_time)
                    info.compress_type = original.compress_type
                    info.external_attr = original.external_attr
                    info.create_system = original.create_system
                    info.comment = original.comment
                    info.extra = original.extra
                destination.writestr(info, data)

        new_path.unlink(missing_ok=True)
        temp_path.replace(new_path)
    except Exception:
        temp_path.unlink(missing_ok=True)
        raise

    path.unlink()
    return new_path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("wheel", type=Path)
    parser.add_argument("--old-name", required=True)
    parser.add_argument("--new-name", required=True)
    parser.add_argument(
        "--replace-requires",
        action="append",
        nargs=2,
        metavar=("OLD", "NEW"),
        default=[],
    )
    args = parser.parse_args()

    result = rewrite_wheel(
        args.wheel,
        args.old_name,
        args.new_name,
        args.replace_requires,
    )
    print(result)


if __name__ == "__main__":
    main()
