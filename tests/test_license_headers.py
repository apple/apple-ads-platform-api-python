# Copyright (c) 2026 Apple Inc. Licensed under MIT License.
from pathlib import Path

LICENSE_HEADER_FILE = Path(__file__).parent.parent / "LICENSE_HEADER.txt"
EXPECTED_HEADER = LICENSE_HEADER_FILE.read_text().strip().splitlines()[0]

SOURCE_DIRS = [
    Path("apple_ads_platform"),
    Path("tests"),
]

EXCLUDED = {
    "apple_ads_platform/__init__.py",
}


def _find_python_files():
    files = []
    for source_dir in SOURCE_DIRS:
        for f in source_dir.rglob("*.py"):
            if str(f) not in EXCLUDED:
                files.append(f)
    return files


def test_all_source_files_have_license_header():
    missing = []
    for f in _find_python_files():
        content = f.read_text()
        if EXPECTED_HEADER not in content.split("\n")[:5]:
            missing.append(str(f))
    assert not missing, (
        f"License header missing from {len(missing)} file(s):\n"
        + "\n".join(f"  {f}" for f in sorted(missing))
    )
