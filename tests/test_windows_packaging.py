"""Check the portable distribution layout without requiring a Windows compiler."""
from pathlib import Path
from zipfile import ZipFile

import pytest

import package_release


@pytest.mark.parametrize('has_license', [False, True])
def test_portable_archive_keeps_executable_and_internal_files(tmp_path: Path, monkeypatch, has_license: bool) -> None:
    source = tmp_path / 'dist' / 'Lumination'
    (source / '_internal').mkdir(parents=True)
    (source / 'Lumination.exe').write_bytes(b'MZ-test-fixture')
    (source / '_internal' / 'dependency.dll').write_bytes(b'test-dependency')
    if has_license:
        (tmp_path / 'LICENSE').write_text('Test license text', encoding='utf-8')
    destination = tmp_path / 'release' / 'Lumination'
    monkeypatch.setattr(package_release, 'ROOT_DIR', str(tmp_path))
    monkeypatch.setattr(package_release, 'DIST_DIR', str(source))
    monkeypatch.setattr(package_release, 'RELEASE_DIR', str(destination))

    package_release.main()

    with ZipFile(tmp_path / 'release' / 'Lumination-windows-x64.zip') as archive:
        assert archive.read('Lumination/Lumination.exe') == b'MZ-test-fixture'
        assert archive.read('Lumination/_internal/dependency.dll') == b'test-dependency'
        assert 'Extract the entire ZIP' in archive.read('Lumination/README_QUICKSTART.txt').decode('utf-8')
        assert ('Lumination/LICENSE' in archive.namelist()) == has_license


def test_windows_packaging_rejects_a_missing_executable(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(package_release, 'DIST_DIR', str(tmp_path / 'missing'))
    with pytest.raises(SystemExit, match='Build Lumination.spec on Windows'):
        package_release.main()
