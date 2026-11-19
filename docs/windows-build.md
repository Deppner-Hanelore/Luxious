# Windows preview build

The GitHub Actions workflow `Windows preview build` runs on Windows Server 2022 with Python 3.12 x64. It tests the source, builds with PyInstaller, and launches the actual bundled executable to check Qt rendering, manual readings including zero, SciPy reconstruction, project save/reload, and CSV/PDF/PNG exports. It then uploads a portable ZIP and build diagnostics/checksum. Artifacts expire after 14 days.

Download the `Lumination-windows-x64` artifact from the successful workflow run, extract the whole ZIP, and open `Lumination/Lumination.exe`. Keep `_internal` beside the executable. No Python installation is required. The archive includes the source commit, resolved dependency versions, and packaged smoke-test result. A repository `LICENSE` file is copied when present.

For a local build, run these commands in PowerShell **on Windows** from the project directory:

```powershell
py -3.12 -m venv .venv-build
.\.venv-build\Scripts\python.exe -m pip install -r requirements-windows-build.txt
.\.venv-build\Scripts\python.exe -m PyInstaller --noconfirm --clean Lumination.spec
.\.venv-build\Scripts\python.exe package_release.py
```

Output: `release/Lumination-windows-x64.zip`. The spec is a one-folder build, rather than a single self-extracting executable. PyInstaller is not a Windows cross-compiler: running it on Linux produces Linux binaries.

This is an unsigned preview, not an installer or a qualified field release. Code signing, clean-machine Windows/user acceptance testing, full localization/accessibility, and physical meter qualification are separate release tasks. Do not enable physical capture merely because the application was packaged successfully.
