# PyQt5-WinARM64

Native Windows ARM64 builds of PyQt5.

> PyQt5-WinARM64 exists because upstream distributes PyQt5 for Windows x86/x64 but not native Windows ARM64, despite the underlying stack being capable of supporting it.

This repository builds and validates PyQt5 against a native Windows ARM64 CPython and a native ARM64 Qt 5.15.19 build.

## Current release

**PyQt5-WinARM64 5.15.11**

The first release provides native Windows ARM64 wheels for:

- PyQt5 5.15.11
- PyQt5-sip 12.15.0

The PyQt5 wheel uses the standard `cp38-abi3-win_arm64` ABI tag, while PyQt5-sip is built for CPython 3.13 ARM64 as `cp313-cp313-win_arm64`.

## Installation

Install the native ARM64 distribution from PyPI:

```powershell
python -m pip install PyQt5-WinARM64
```

PyQt5-sip is pulled in as the matching `PyQt5-sip-WinARM64` dependency.

The Python import namespace remains the standard PyQt5 namespace:

```python
from PyQt5.QtWidgets import QApplication

app = QApplication([])
```

The distribution is specifically for **native Windows ARM64** Python. It is not an x64 compatibility build.

## Build and validation boundary

The project deliberately validates the stack in stages:

1. Native Windows ARM64 runner
2. ARM64 CPython
3. ARM64 MSVC
4. Native ARM64 Qt 5.15.19
5. PyQt5-sip
6. PyQt5
7. Native Qt runtime bundling
8. ARM64 PE validation
9. Clean ARM64 installation
10. `QApplication` smoke test

No wheel release is considered valid until a clean ARM64 environment can install the wheels, import PyQt5, and create a `QApplication`.

The current CI validation covers:

- native Windows ARM64 GitHub Actions runner
- CPython 3.13 ARM64
- MSVC ARM64
- Qt 5.15.19 built natively for ARM64
- PyQt5-sip 12.15.0
- PyQt5 5.15.11 as an ARM64 `abi3` wheel
- bundled Qt runtime
- ARM64 PE headers for every bundled `.pyd` and `.dll`
- clean ARM64 virtual-environment installation
- `QApplication([])` startup

## Distribution names

The upstream PyPI projects `PyQt5` and `PyQt5-sip` already exist, so this project publishes distinct distribution names:

- `PyQt5-WinARM64`
- `PyQt5-sip-WinARM64`

The installed Python modules remain `PyQt5` and `PyQt5.sip`/SIP's normal extension namespace.

## Build inputs

The release pipeline pins and verifies:

- PyQt5 5.15.11
- PyQt5-sip 12.15.0
- SIP 6.8.6
- PyQt-builder 1.17.0
- Qt 5.15.19
- WinFlexBison 2.5.25

The PyQt5, PyQt5-sip, and Qt source archives are SHA-256 verified before use.

The GitHub Actions release workflow uses PyPI Trusted Publishing (OIDC). No long-lived PyPI API token is stored in the repository.

## Release wheels

The 5.15.11 release contains:

- `pyqt5_winarm64-5.15.11-cp38-abi3-win_arm64.whl`
- `pyqt5_sip_winarm64-12.15.0-cp313-cp313-win_arm64.whl`

## Licensing

This repository's build and automation code is MIT licensed.

The produced PyQt5 distribution contains software under its upstream licenses. PyQt5 5.15.11 is GPLv3 (with Riverbank's commercial licensing option), PyQt5-sip is BSD-2-Clause, and the bundled Qt components are distributed under their applicable Qt licenses. The wheel carries the relevant upstream license files.

## Project

GitHub: https://github.com/ViciousSquid/PyQt5-WinARM64
