# SPDX-License-Identifier: BSD-2-Clause

from pathlib import Path
from setuptools import Extension, setup

ROOT = Path(__file__).resolve().parent
sources = sorted(str(p) for p in ROOT.glob("*.c"))

sip = Extension(
    "PyQt5.sip",
    sources=sources,
    include_dirs=[str(ROOT)],
    define_macros=[("Py_LIMITED_API", "0x030C0000")],
    py_limited_api=True,
)

setup(
    name="PyQt5-sip-WinARM64",
    version="12.15.0",
    description="SIP 6.8.6 ABI3 runtime for PyQt5 on Windows ARM64",
    python_requires=">=3.12",
    ext_modules=[sip],
)
