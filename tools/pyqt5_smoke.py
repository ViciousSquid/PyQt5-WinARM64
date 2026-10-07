from PyQt5.QtCore import QT_VERSION_STR, QTimer
from PyQt5.QtWidgets import QApplication, QLabel, QWidget


def main() -> None:
    app = QApplication([])

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

    print(f"PyQt5-WinARM64 smoke test passed (Qt {QT_VERSION_STR})")


if __name__ == "__main__":
    main()
