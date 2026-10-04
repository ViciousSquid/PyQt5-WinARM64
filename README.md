# PyQt5-WinARM64

Native Windows ARM64 builds of PyQt5.

This repository builds and validates PyQt5 against a native Windows ARM64 CPython and a native ARM64 Qt 5.15.x build.

## Build boundary

The project deliberately validates the stack in stages:

1. Native Windows ARM64 runner
2. ARM64 CPython
3. ARM64 MSVC
4. Native ARM64 Qt 5.15.x
5. PyQt5-sip
6. PyQt5
7. ARM64 wheel validation

No wheel release is considered valid until a clean ARM64 environment can import PyQt5 and create a QApplication.

## Status

Bootstrap: native Windows ARM64 runner validation.
