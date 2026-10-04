# PyQt5-WinARM64

Native Windows ARM64 builds of PyQt5.

> PyQt5-WinARM64 exists because upstream distributes PyQt5 for Windows x86/x64 but not native Windows ARM64, despite the underlying stack being capable of supporting it.

This repository builds and validates PyQt5 against a native Windows ARM64 CPython and a native ARM64 Qt 5.15.x build.

## Build boundary

The project deliberately validates the stack in stages:

1. Native Windows ARM64 runner
2. ARM64 CPython
3. ARM64 MSVC
4. Native ARM64 Qt 5.15.x
5. PyQt5-sip
6. PyQt5
7. Native Qt bundling
8. ARM64 PE validation
9. Clean ARM64 installation
10. `QApplication` smoke test

No wheel release is considered valid until a clean ARM64 environment can import PyQt5 and create a QApplication.

## Current status

**CI-validated native Windows ARM64 build.**

The current pipeline has successfully validated:

- Windows ARM64 GitHub Actions runner
- CPython 3.13 ARM64
- MSVC ARM64
- Qt 5.15.19 built natively for ARM64
- PyQt5-sip 12.19.0 as `cp313-cp313-win_arm64`
- PyQt5 5.15.11 as an ARM64 `abi3` wheel
- bundled Qt runtime
- ARM64 PE headers for bundled `.pyd` and `.dll` files
- clean ARM64 virtual-environment installation
- `QApplication([])` startup

The PyPI release pipeline uses PyPI Trusted Publishing from GitHub Actions. No long-lived PyPI API token is stored in the repository.

## Installation

Once the first PyPI release is published:

```powershell
python -m pip install PyQt5-WinARM64
```

The Python import namespace remains the standard PyQt5 namespace:

```python
from PyQt5.QtWidgets import QApplication

app = QApplication([])
```

The distribution is specifically for **native Windows ARM64** Python. It is not an x64 compatibility build.

## Distribution names

The upstream PyPI projects `PyQt5` and `PyQt5-sip` already exist, so this project publishes distinct distribution names:

- `PyQt5-WinARM64`
- `PyQt5-sip-WinARM64`

The installed Python modules remain `PyQt5` and `PyQt5.sip`/SIP's normal extension namespace.

## Build inputs

The current release pipeline pins and verifies:

- PyQt5 5.15.11
- PyQt5-sip 12.19.0
- SIP 6.16.1
- PyQt-builder 1.19.1
- Qt 5.15.19
- WinFlexBison 2.5.25

Source archives are SHA-256 verified before use.

## Licensing

This repository's build and automation code is MIT licensed.

The produced PyQt5 distribution contains software under its upstream licenses. PyQt5 5.15.11 is GPLv3 (with Riverbank's commercial licensing option), PyQt5-sip is BSD-2-Clause, and the bundled Qt components are distributed under their applicable Qt licenses. The wheel carries the relevant upstream license files.

## Project

GitHub: https://github.com/ViciousSquid/PyQt5-WinARM64
