#!/usr/bin/env python3
"""Strictly validate a PyQt5-WinARM64 or PyQt5-sip-WinARM64 wheel.

Checks that pip will be able to install and later read back the wheel:
the filename parses, the .dist-info directory matches the normalized name and
version, METADATA agrees with the filename, and every RECORD hash is correct.
For the PyQt5 wheel it also requires the bundled Qt runtime, platform plugin
and MSVC runtime to be present, so a wheel without Qt can never be released
again.

Pure standard library so it runs anywhere (Linux publish job included).
"""

from __future__ import annotations

import argparse
import base64
import csv
import hashlib
import io
import re
import sys
import zipfile
from pathlib import Path

PYQT5_REQUIRED = [
    "PyQt5/QtCore.pyd",
    "PyQt5/QtGui.pyd",
    "PyQt5/QtWidgets.pyd",
    "PyQt5/Qt5/bin/Qt5Core.dll",
    "PyQt5/Qt5/bin/Qt5Gui.dll",
    "PyQt5/Qt5/bin/Qt5Widgets.dll",
    "PyQt5/Qt5/bin/msvcp140.dll",
    "PyQt5/Qt5/bin/vcruntime140.dll",
    "PyQt5/Qt5/plugins/platforms/qwindows.dll",
]

SIP_REQUIRED_PATTERN = re.compile(r"^PyQt5/sip\.cp\d+-win_arm64\.pyd$")


def normalize(name: str) -> str:
    return re.sub(r"[-_.]+", "_", name).lower()


def fail(message: str) -> None:
    raise SystemExit(f"FAIL: {message}")


def header(metadata: str, key: str) -> str:
    match = re.search(rf"(?m)^{key}:[ \t]*([^\r\n]+?)[ \t]*\r?$", metadata)
    if match is None:
        fail(f"METADATA has no {key} header")
    return match.group(1)


def verify(path: Path, expect_version: str | None) -> None:
    stem = path.name[:-4] if path.name.endswith(".whl") else fail(f"not a wheel: {path.name}")
    parts = stem.split("-")
    if len(parts) != 5:
        fail(f"{path.name}: expected name-version-python-abi-platform with no build tag")
    distribution, version, _py, _abi, platform = parts
    if platform != "win_arm64":
        fail(f"{path.name}: platform tag is {platform!r}, expected 'win_arm64'")
    if distribution != normalize(distribution):
        fail(f"{path.name}: distribution part is not normalized")
    if expect_version and version != expect_version:
        fail(f"{path.name}: version {version!r}, expected {expect_version!r}")

    dist_info = f"{distribution}-{version}.dist-info"

    with zipfile.ZipFile(path) as wheel:
        names = [n for n in wheel.namelist() if not n.endswith("/")]
        dist_infos = {n.split("/", 1)[0] for n in names if n.split("/", 1)[0].endswith(".dist-info")}
        if dist_infos != {dist_info}:
            fail(f"{path.name}: .dist-info directories {sorted(dist_infos)}, expected ['{dist_info}']")

        for required in ("METADATA", "WHEEL", "RECORD"):
            if f"{dist_info}/{required}" not in names:
                fail(f"{path.name}: missing {dist_info}/{required}")

        metadata = wheel.read(f"{dist_info}/METADATA").decode("utf-8")
        if normalize(header(metadata, "Name")) != distribution:
            fail(f"{path.name}: METADATA Name does not match filename")
        if header(metadata, "Version") != version:
            fail(f"{path.name}: METADATA Version does not match filename")

        wheel_text = wheel.read(f"{dist_info}/WHEEL").decode("utf-8")
        if "Build:" in wheel_text:
            fail(f"{path.name}: WHEEL declares a build tag but the filename has none")

        record = list(csv.reader(io.StringIO(wheel.read(f"{dist_info}/RECORD").decode("utf-8"))))
        recorded = {}
        for row in record:
            if len(row) != 3:
                fail(f"{path.name}: malformed RECORD row {row!r}")
            recorded[row[0]] = row
        if set(recorded) != set(names):
            missing = sorted(set(names) - set(recorded))
            extra = sorted(set(recorded) - set(names))
            fail(f"{path.name}: RECORD mismatch; unrecorded={missing[:5]} absent={extra[:5]}")
        for name, (_, hash_value, size) in recorded.items():
            if name == f"{dist_info}/RECORD":
                continue
            data = wheel.read(name)
            expected = "sha256=" + base64.urlsafe_b64encode(hashlib.sha256(data).digest()).rstrip(b"=").decode("ascii")
            if hash_value != expected or size != str(len(data)):
                fail(f"{path.name}: RECORD hash/size mismatch for {name}")

        if distribution == "pyqt5_winarm64":
            missing = [r for r in PYQT5_REQUIRED if r not in names]
            if missing:
                fail(f"{path.name}: bundled Qt runtime is incomplete; missing {missing}")
            if "Requires-Dist: PyQt5-sip-WinARM64" not in metadata:
                fail(f"{path.name}: METADATA must require PyQt5-sip-WinARM64")
            if re.search(r"(?mi)^Requires-Dist:\s*PyQt5-sip\b(?!-WinARM64)", metadata):
                fail(f"{path.name}: METADATA still requires upstream PyQt5-sip")
            dll_count = sum(1 for n in names if n.startswith("PyQt5/Qt5/") and n.lower().endswith(".dll"))
            print(f"{path.name}: {dll_count} bundled Qt/runtime DLLs")
        elif distribution == "pyqt5_sip_winarm64":
            if not any(SIP_REQUIRED_PATTERN.match(n) for n in names):
                fail(f"{path.name}: no PyQt5/sip.cpXY-win_arm64.pyd extension module")
        else:
            fail(f"{path.name}: unexpected distribution {distribution!r}")

    print(f"OK: {path.name} ({path.stat().st_size:,} bytes)")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("wheels", nargs="+", type=Path)
    parser.add_argument("--expect-version", help="require this distribution version")
    args = parser.parse_args()
    for wheel in args.wheels:
        verify(wheel, args.expect_version)


if __name__ == "__main__":
    sys.exit(main())
