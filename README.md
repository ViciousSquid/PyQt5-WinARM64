# PyQt5-WinARM64

Native Windows ARM64 builds of PyQt5.

> PyQt5-WinARM64 exists because upstream distributes PyQt5 for Windows x86/x64 but not native Windows ARM64, despite the underlying stack being capable of supporting it.

This repository builds and validates PyQt5 against a native Windows ARM64 CPython and a native ARM64 Qt 5.15.19 build.

> [!WARNING]
> **PyQt5-WinARM64 5.15.11 is broken: upgrade to 5.15.11.post1.**
> The 5.15.11 wheel was published without the Qt runtime (`Qt5Core.dll` and friends), so `import PyQt5.QtCore` fails with
> `DLL load failed` unless a native ARM64 Qt happens to be on `PATH`. The wheels attached to the 5.15.11 GitHub release
> also had malformed metadata that makes pip crash with `InvalidVersion: 'info'`. Upgrade with
> `python -m pip install --upgrade PyQt5-WinARM64`. See [Known issues](#known-issues-in-51511) for clean-up steps.

## Current release

**PyQt5-WinARM64 5.15.11.post1**

| Wheel | For |
| --- | --- |
| `pyqt5_winarm64-5.15.11.post1-cp39-abi3-win_arm64.whl` | CPython 3.9+ on Windows ARM64 |
| `pyqt5_sip_winarm64-12.17.0-cp313-cp313-win_arm64.whl` | CPython 3.13 |
| `pyqt5_sip_winarm64-12.17.0-cp314-cp314-win_arm64.whl` | CPython 3.14 |

- PyQt5 5.15.11, built against Qt 5.15.19 (qtbase) natively for ARM64
- The Qt runtime and Qt plugins are bundled in `PyQt5\Qt5`
- The ARM64 MSVC C++ runtime is bundled, so the Visual C++ Redistributable is not required
- PyQt5-sip 12.17.0 for CPython 3.13 and 3.14

The PyQt5 wheel uses the Stable ABI (`cp39-abi3`), so one wheel serves every supported CPython version. The SIP wheel is
specific to each CPython version, and pip picks the right one automatically.

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

## Known issues in 5.15.11

5.15.11 should not be used.

- **No Qt runtime (PyPI and GitHub release).** pyqt-bundle writes its output to the current directory, and the release
  workflow packaged the unbundled wheel it found in `dist\` instead. The smoke test still passed because the build
  runner's own Qt was on `PATH`, and a failing `pip install` in that step was not checked.
- **Malformed metadata (GitHub release assets only).** The wheels attached to the 5.15.11 GitHub release contain
  `pyqt5_winarm64-info.dist-info` and `pyqt5_sip_winarm64-info.dist-info`. pip installs them, but then crashes with
  `InvalidVersion: 'info'` whenever it lists installed packages. The PyPI copies of 5.15.11 do not have this problem.

To recover:

```powershell
python -m pip install --upgrade PyQt5-WinARM64
```

If pip itself crashes with `InvalidVersion: 'info'`, delete these folders from your environment's `Lib\site-packages`
first, then run the install again:

- `pyqt5_winarm64-info.dist-info`
- `pyqt5_sip_winarm64-info.dist-info`
- `PyQt5`

## Build and validation

The project deliberately validates the stack in stages:

1. Native Windows ARM64 runner
2. ARM64 CPython
3. ARM64 MSVC
4. Native ARM64 Qt 5.15.19
5. PyQt5-sip for each supported CPython version
6. PyQt5
7. Native Qt runtime and MSVC runtime bundling
8. Wheel validation (`tools/verify_wheel.py`): `.dist-info` name, METADATA, every `RECORD` hash, and the presence of the
   Qt runtime and `qwindows` platform plugin
9. ARM64 PE validation of every `.pyd` and `.dll`
10. Clean installation **on a fresh runner with no Qt on the machine**, on CPython 3.13 and 3.14
11. Smoke test (`tools/pyqt5_smoke.py`) that fails unless Qt is loaded from the installed wheel itself

No wheel is released until every stage passes. The PyPI publish workflow runs `tools/verify_wheel.py` again before it
uploads anything.

## Releasing

1. Run **PyQt5 ARM64 wheel** on `main` with `release_tag` set to `v<PYQT5_DIST_VERSION>`. After the build and the
   clean-install tests pass, it creates the GitHub release from the verified wheels and
   `.github/release-notes/<tag>.md`.
2. Run **Publish PyQt5 Windows ARM64** with the same tag to upload to PyPI (Trusted Publishing).
3. Run **ARM64 Release Smoke Test** with `from_pypi` checked to confirm what users actually get from PyPI.

## Distribution names

The upstream PyPI projects `PyQt5` and `PyQt5-sip` already exist, so this project publishes distinct distribution names:

- `PyQt5-WinARM64`
- `PyQt5-sip-WinARM64`

The installed Python modules remain `PyQt5` and `PyQt5.sip`/SIP's normal extension namespace.

## Build inputs

The release pipeline pins and verifies:

- PyQt5 5.15.11 (published as 5.15.11.post1)
- PyQt5-sip 12.17.0
- SIP 6.10.0
- PyQt-builder 1.17.0
- Qt 5.15.19
- WinFlexBison 2.5.25

The PyQt5, PyQt5-sip, and Qt source archives are SHA-256 verified before use.

The GitHub Actions release workflow uses PyPI Trusted Publishing (OIDC). No long-lived PyPI API token is stored in the repository.

## Licensing

This repository's build and automation code is MIT licensed.

The produced PyQt5 distribution contains software under its upstream licenses. PyQt5 5.15.11 is GPLv3 (with Riverbank's commercial licensing option), PyQt5-sip is BSD-2-Clause, the bundled Qt components are distributed under their applicable Qt licenses, and the bundled Microsoft Visual C++ runtime DLLs are redistributed under the Visual Studio redistributable terms. The wheel carries the relevant upstream license files.

## Project

GitHub: https://github.com/ViciousSquid/PyQt5-WinARM64
