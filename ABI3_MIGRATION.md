# SIP 6.8.6 → Python 3.12+ Stable ABI migration

## State

- **Branch:** `abi3/sip-6.8.6-cp312`
- **Starting commit:** `11f95eeefefe9c68c8795896351dd49e233e2338`
- **Starting main/release state:** unchanged; existing `v5.15.11` release is not modified or retagged.
- **Exact upstream runtime:** Python-SIP `6.8.6`, ABI 12.15.0, source tree `sipbuild/module/source/12`.
- **Target:** `Py_LIMITED_API=0x030C0000` / `cp312-abi3`.
- **Current phase:** bootstrap and architectural type-system conversion.
- **Last completed step:** dedicated branch created from the exact starting HEAD.

## Chronology

### 2026-10-06 — branch and source baseline

Created `abi3/sip-6.8.6-cp312` directly from main commit `11f95eeefefe9c68c8795896351dd49e233e2338`.

The existing PyQt5-WinARM64 5.15.11 release remains outside this branch's release path. No existing release/tag is changed.

Vendored the exact SIP 6.8.6 ABI 12.15 runtime source used to build PyQt5-sip 12.15.0. The vendored files correspond to Python-SIP tag `6.8.6`; the original `sip.h.in` is retained and a concrete `sip.h` is generated for the PyQt5.sip module identity.

### Source audit

The runtime contains these architectural dependencies on the non-limited CPython layout:

- `siplib.c`: 6 `PyHeapTypeObject` references; static `PyTypeObject` definitions; extensive direct `tp_*`, `tp_as_*`, `nb_*`, `sq_*`, `mp_*`, and `am_*` access; custom wrapper metadata embedded after the Python type object.
- `descriptors.c`: two static type definitions and direct `tp_free` calls.
- `sip_array.c`: static type definition and direct `tp_alloc`.
- `voidptr.c`: static type definition and direct `tp_alloc`.
- `siplib.c` also reads/writes the custom wrapper fields `wt_user_type`, `wt_dict_complete`, `wt_td`, `wt_iextend`, `wt_new_user_type_handler`, and `wt_user_data`.

The central non-ABI3 design is the old `sipWrapperType` layout: it embeds `PyHeapTypeObject` and appends SIP-owned type metadata. The conversion must move that metadata into Stable-ABI type data returned by `PyObject_GetTypeData()`.

## Architectural decisions

1. Python 3.12 is the ABI floor. The build must define `Py_LIMITED_API=0x030C0000` and produce a true `cp312-abi3` extension.
2. Wrapper metadata will become SIP-owned type data allocated through `PyType_Spec.basicsize < 0`, accessed with `PyObject_GetTypeData()`.
3. SIP-defined Python types will be created from `PyType_Spec`/`PyType_Slot`, not static `PyTypeObject` initializers.
4. Generated wrapper numeric/sequence/mapping/async/buffer behavior will be supplied as `PyType_Slot` entries during type creation. Post-creation structure mutation is not an accepted solution.
5. Direct access to opaque `PyTypeObject` fields will be removed in favor of Stable-ABI APIs such as `PyType_GetSlot()`, `PyType_GetDict()`, `PyType_GetName()`, `PyType_GetQualName()`, `PyType_GetFlags()`, and `PyObject_GetTypeData()`.
6. No compatibility shims, `getattr`-style fallbacks, fake legacy layouts, or dual implementation paths will be introduced.

## Build configuration added

`sip_abi3/setup.py` defines:

- extension name: `PyQt5.sip`
- runtime version: `12.15.0`
- `Py_LIMITED_API=0x030C0000`
- `py_limited_api=True`
- Python requirement: `>=3.12`

A dedicated ARM64 GitHub Actions workflow will compile this branch on native Windows ARM64 with CPython 3.12 and validate the resulting `cp312-abi3-win_arm64` wheel.

## Tests

Not yet run after the initial bootstrap commit. The first CI run is intentionally the ABI3 compile/smoke-test gate. Its compiler diagnostics will be recorded here and classified by architectural cause rather than suppressed.

## Remaining blockers

The vendored runtime is still the original SIP 6.8.6 implementation. It is expected to fail the first limited-API compilation until the type foundation and subsequent concrete-layout accesses are converted.

## Rejected approaches

- Raising the ABI floor without converting SIP's type layout.
- Suppressing individual compiler errors while retaining concrete CPython structure access.
- Keeping `PyHeapTypeObject` embedded behind a compatibility cast.
- Retaining post-creation slot mutation.

## Exact next step

Run the dedicated CPython 3.12 ARM64 `cp312-abi3` build against the exact vendored SIP 6.8.6 source, record the first complete compiler failure set, then convert the wrapper metatype/wrapper type to `PyType_Spec` + Stable-ABI type data and re-run the build.
