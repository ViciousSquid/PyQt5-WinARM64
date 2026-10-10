"""Clean-machine smoke test for an installed PyQt5-WinARM64.

Fails unless Qt is loaded from the wheel's own PyQt5\\Qt5 directory. A Qt
installation elsewhere on PATH must never be what makes this test pass.
"""

import ctypes
import os
import platform
from ctypes import wintypes
from pathlib import Path

import PyQt5
from PyQt5.QtCore import QT_VERSION_STR, PYQT_VERSION_STR, QLibraryInfo, QTimer
from PyQt5.QtWidgets import QApplication, QLabel, QWidget


def loaded_module_path(name: str) -> Path:
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.GetModuleHandleW.restype = wintypes.HMODULE
    kernel32.GetModuleHandleW.argtypes = [wintypes.LPCWSTR]
    kernel32.GetModuleFileNameW.argtypes = [wintypes.HMODULE, wintypes.LPWSTR, wintypes.DWORD]
    handle = kernel32.GetModuleHandleW(name)
    if not handle:
        raise SystemExit(f"{name} is not loaded")
    buffer = ctypes.create_unicode_buffer(32768)
    kernel32.GetModuleFileNameW(handle, buffer, len(buffer))
    return Path(buffer.value).resolve()


def main() -> None:
    if platform.machine() != "ARM64":
        raise SystemExit(f"Python is not ARM64: {platform.machine()}")

    bundled = (Path(PyQt5.__file__).parent / "Qt5").resolve()
    if not (bundled / "bin" / "Qt5Core.dll").is_file():
        raise SystemExit(f"Bundled Qt runtime not found at {bundled}")

    app = QApplication([])

    for dll in ("Qt5Core.dll", "Qt5Gui.dll", "Qt5Widgets.dll"):
        path = loaded_module_path(dll)
        if bundled not in path.parents:
            raise SystemExit(f"{dll} was loaded from {path}, not from the wheel ({bundled})")

    plugins = Path(QLibraryInfo.location(QLibraryInfo.PluginsPath)).resolve()
    if plugins != bundled / "plugins":
        raise SystemExit(f"Qt plugin path is {plugins}, expected {bundled / 'plugins'}")
    if app.platformName() != "windows":
        raise SystemExit(f"Unexpected Qt platform plugin: {app.platformName()}")

    window = QWidget()
    window.setWindowTitle("PyQt5-WinARM64 smoke test")
    window.resize(240, 64)

    label = QLabel("PyQt5-WinARM64 OK", parent=window)
    label.move(16, 20)

    window.show()

    QTimer.singleShot(100, app.quit)
    exit_code = app.exec_()

    if exit_code != 0:
        raise SystemExit(f"Qt event loop exited with code {exit_code}")

    print(f"Qt runtime: {loaded_module_path('Qt5Core.dll')}")
    print(f"PATH entries: {len(os.environ.get('PATH', '').split(os.pathsep))}")
    print(f"PyQt5-WinARM64 smoke test passed (PyQt {PYQT_VERSION_STR}, Qt {QT_VERSION_STR})")


if __name__ == "__main__":
    main()
