#!/usr/bin/env python3
"""Retag a wheel distribution without changing its import package.

Renames the distribution (and optionally its version), rewrites the matching
Requires-Dist entries, can add extra files, and always regenerates RECORD so
the result is a valid wheel. The version is read from METADATA rather than
parsed out of directory names, and the .dist-info directory is always named
from the normalized name and version so pip can read it back.

Selected METADATA headers (Requires-Python, Summary, Author-email) can be
replaced, Project-URL entries rewritten and the long description replaced
from a file, so a retagged distribution presents its own metadata instead
of upstream's.
"""

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


def digest(data: bytes) -> str:
    encoded = base64.urlsafe_b64encode(hashlib.sha256(data).digest()).rstrip(b"=")
    return f"sha256={encoded.decode('ascii')}"


def split_wheel_filename(name: str) -> tuple[str, str, str | None, str]:
    """Return (distribution, version, build tag, python-abi-platform tags)."""
    if not name.lower().endswith(".whl"):
        raise ValueError(f"not a wheel filename: {name}")
    parts = name[:-4].split("-")
    if len(parts) == 5:
        distribution, version, py, abi, plat = parts
        build = None
    elif len(parts) == 6:
        distribution, version, build, py, abi, plat = parts
    else:
        raise ValueError(f"unrecognised wheel filename: {name}")
    return distribution, version, build, f"{py}-{abi}-{plat}"


def apply_metadata_overrides(
    metadata: str,
    requires_python: str | None = None,
    summary: str | None = None,
    author_email: str | None = None,
    description_file: Path | None = None,
    project_urls: list[tuple[str, str]] | None = None,
) -> str:
    """Replace selected METADATA headers and the long description.

    Header overrides only ever replace an existing header, never invent
    one: a requested override whose key is absent from the source metadata
    is an error, so an unexpected upstream METADATA layout cannot pass
    silently. Project-URL entries are the exception: existing entries are
    dropped so stale upstream links do not outlive the retag.
    """
    lines = metadata.splitlines(keepends=True)
    blank = next((i for i, line in enumerate(lines) if not line.strip()), len(lines))
    headers, body = lines[:blank], lines[blank:]

    replacements = {
        "Requires-Python": requires_python,
        "Summary": summary,
        "Author-email": author_email,
    }
    rewritten: list[str] = []
    for line in headers:
        override = next(
            (
                key
                for key, value in replacements.items()
                if value is not None and re.match(rf"(?i)^{re.escape(key)}:[ \t]", line)
            ),
            None,
        )
        if override is None:
            if project_urls is not None and re.match(r"(?i)^Project-URL:[ \t]", line):
                continue
            rewritten.append(line)
        else:
            newline = "\r\n" if line.endswith("\r\n") else "\n"
            rewritten.append(f"{override}: {replacements[override]}{newline}")
            replacements[override] = None

    for key, value in replacements.items():
        if value is not None:
            raise ValueError(f"wheel metadata does not declare a {key} header; cannot override it")

    if project_urls is not None:
        rewritten.extend(f"Project-URL: {label}, {url}\n" for label, url in project_urls)

    headers_text = "".join(rewritten)
    if description_file is None:
        return headers_text + "".join(body)
    text = description_file.read_text(encoding="utf-8")
    if not text.endswith("\n"):
        text += "\n"
    return headers_text + "\n" + text


def rewrite_wheel(
    path: Path,
    old_name: str,
    new_name: str,
    requirements: list[tuple[str, str]],
    new_version: str | None = None,
    drop_build_tag: bool = False,
    added_files: list[tuple[Path, str]] | None = None,
    output_dir: Path | None = None,
    requires_python: str | None = None,
    summary: str | None = None,
    author_email: str | None = None,
    description_file: Path | None = None,
    project_urls: list[tuple[str, str]] | None = None,
) -> Path:
    distribution, file_version, build_tag, tags = split_wheel_filename(path.name)
    if normalize_wheel_name(distribution) != normalize_wheel_name(old_name):
        raise ValueError(f"wheel filename does not start with distribution {old_name!r}: {path.name}")

    with zipfile.ZipFile(path, "r") as source:
        entries = [(info, source.read(info.filename)) for info in source.infolist()]

    metadata_entries = [info.filename for info, _ in entries if info.filename.endswith(".dist-info/METADATA")]
    if len(metadata_entries) != 1:
        raise ValueError(f"expected exactly one .dist-info/METADATA in {path}, found {len(metadata_entries)}")
    metadata_name = metadata_entries[0]
    old_dist_info = metadata_name.rsplit("/", 1)[0]

    metadata = next(data for info, data in entries if info.filename == metadata_name).decode("utf-8")

    # Core metadata and wheel filenames use distribution-name normalization:
    # runs of '-', '_' and '.' are equivalent for matching purposes.
    name_match = re.search(r"(?m)^(Name:[ \t]*)([^\r\n]+?)[ \t]*\r?$", metadata)
    if name_match is None or normalize_wheel_name(name_match.group(2)) != normalize_wheel_name(old_name):
        raise ValueError(f"wheel metadata does not declare Name: {old_name}")
    metadata = metadata[: name_match.start(2)] + new_name + metadata[name_match.end(2) :]

    version_match = re.search(r"(?m)^(Version:[ \t]*)([^\r\n]+?)[ \t]*\r?$", metadata)
    if version_match is None:
        raise ValueError("wheel metadata does not declare a Version")
    old_version = version_match.group(2)
    if old_version != file_version:
        raise ValueError(f"METADATA version {old_version!r} does not match filename version {file_version!r}")
    version = new_version or old_version
    metadata = metadata[: version_match.start(2)] + version + metadata[version_match.end(2) :]

    for old_requirement, new_requirement in requirements:
        requirement_pattern = re.compile(r"(?im)^(Requires-Dist:\s*)([^\s;(<>=!~\[]+)")

        def replace_requirement(match: re.Match[str]) -> str:
            if normalize_wheel_name(match.group(2)) == normalize_wheel_name(old_requirement):
                return match.group(1) + new_requirement
            return match.group(0)

        metadata = requirement_pattern.sub(replace_requirement, metadata)

    metadata = apply_metadata_overrides(
        metadata,
        requires_python=requires_python,
        summary=summary,
        author_email=author_email,
        description_file=description_file,
        project_urls=project_urls,
    )

    new_dist_info = f"{normalize_wheel_name(new_name)}-{version}.dist-info"
    record_name = new_dist_info + "/RECORD"

    rewritten: list[tuple[str, bytes, zipfile.ZipInfo | None]] = []
    for info, data in entries:
        name = info.filename
        if name.endswith("/"):
            continue
        if name.startswith(old_dist_info + "/"):
            name = new_dist_info + name[len(old_dist_info) :]
        if name == record_name:
            continue
        if name == new_dist_info + "/METADATA":
            data = metadata.encode("utf-8")
        if name == new_dist_info + "/WHEEL" and drop_build_tag:
            text = data.decode("utf-8")
            data = "".join(line for line in text.splitlines(keepends=True) if not line.startswith("Build:")).encode("utf-8")
        rewritten.append((name, data, info))

    existing = {name for name, _, _ in rewritten}
    for source_path, arcname in added_files or []:
        arcname = arcname.replace("\\", "/")
        if arcname in existing:
            raise ValueError(f"refusing to overwrite existing wheel entry: {arcname}")
        rewritten.append((arcname, source_path.read_bytes(), None))
        existing.add(arcname)

    record_rows = [[name, digest(data), str(len(data))] for name, data, _ in rewritten]
    record_rows.append([record_name, "", ""])
    output = io.StringIO()
    csv.writer(output, lineterminator="\n").writerows(record_rows)
    rewritten.append((record_name, output.getvalue().encode("utf-8"), None))

    filename_parts = [normalize_wheel_name(new_name), version]
    if build_tag and not drop_build_tag:
        filename_parts.append(build_tag)
    filename_parts.append(tags)
    target_dir = output_dir or path.parent
    target_dir.mkdir(parents=True, exist_ok=True)
    new_path = target_dir / ("-".join(filename_parts) + ".whl")

    with tempfile.NamedTemporaryFile(delete=False, suffix=".whl", dir=target_dir) as temp:
        temp_path = Path(temp.name)

    try:
        with zipfile.ZipFile(temp_path, "w") as destination:
            for name, data, original in rewritten:
                if original is None:
                    info = zipfile.ZipInfo(name, date_time=(2026, 1, 1, 0, 0, 0))
                    info.compress_type = zipfile.ZIP_DEFLATED
                    info.external_attr = 0o644 << 16
                else:
                    info = zipfile.ZipInfo(name, date_time=original.date_time)
                    info.compress_type = original.compress_type
                    info.external_attr = original.external_attr
                    info.create_system = original.create_system
                destination.writestr(info, data)

        same_file = new_path.resolve() == path.resolve()
        if not same_file:
            new_path.unlink(missing_ok=True)
        temp_path.replace(new_path)
    except Exception:
        temp_path.unlink(missing_ok=True)
        raise

    if not same_file:
        path.unlink()
    return new_path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("wheel", type=Path)
    parser.add_argument("--old-name", required=True)
    parser.add_argument("--new-name", required=True)
    parser.add_argument("--new-version", help="replace the distribution version (e.g. 5.15.11.post1)")
    parser.add_argument("--drop-build-tag", action="store_true", help="remove the wheel build tag")
    parser.add_argument("--output-dir", type=Path, help="write the result here instead of next to the input")
    parser.add_argument(
        "--replace-requires",
        action="append",
        nargs=2,
        metavar=("OLD", "NEW"),
        default=[],
    )
    parser.add_argument(
        "--add-file",
        action="append",
        nargs=2,
        metavar=("SOURCE", "ARCNAME"),
        default=[],
        help="add a file to the wheel at the given archive path",
    )
    parser.add_argument("--set-requires-python", help="replace the Requires-Python header")
    parser.add_argument("--set-summary", help="replace the Summary header")
    parser.add_argument("--set-author-email", help="replace the Author-email header")
    parser.add_argument(
        "--description-file",
        type=Path,
        help="replace the long description with this file's contents",
    )
    parser.add_argument(
        "--project-url",
        action="append",
        nargs=2,
        metavar=("LABEL", "URL"),
        default=[],
        help="replace the Project-URL entries with LABEL, URL (repeatable)",
    )
    args = parser.parse_args()

    result = rewrite_wheel(
        args.wheel,
        args.old_name,
        args.new_name,
        args.replace_requires,
        new_version=args.new_version,
        drop_build_tag=args.drop_build_tag,
        added_files=[(Path(source), arcname) for source, arcname in args.add_file],
        output_dir=args.output_dir,
        requires_python=args.set_requires_python,
        summary=args.set_summary,
        author_email=args.set_author_email,
        description_file=args.description_file,
        project_urls=[(label, url) for label, url in args.project_url] or None,
    )
    print(result)


if __name__ == "__main__":
    main()
