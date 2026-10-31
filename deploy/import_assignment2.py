"""Preview and import only Assignment 2 deployment files into an existing Git checkout.

No network, Git commits, application launch, private configuration or database changes.
Run with Python 3.12 from the extracted package. See the Windows guide first.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

SOURCE = Path(__file__).resolve().parents[1]
PATCH_FILES = ("ui/bootstrap.php", "services/payment/src/platform.php",
               "services/notification/src/platform.php", ".gitignore")
REQUIRED = ("requirements.lock.txt", "scripts/common.py", "scripts/e2e.py",
            "services/inventory/database/schema.sql", "services/reservation/database/schema.sql",
            "services/payment/database/schema.sql", "services/notification/database/schema.sql")


def git(target: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["git", "-C", str(target), *args], capture_output=True, text=True)


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def safe_file(root: Path, relative: str) -> Path:
    path = root / relative
    if not path.resolve().is_relative_to(root.resolve()):
        raise ValueError("Path escapes project: " + relative)
    if path.is_symlink():
        raise ValueError("Refusing a symbolic link: " + relative)
    return path


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--target", required=True, type=Path, help="Existing project Git root")
    ap.add_argument("--apply", action="store_true", help="Apply the previewed import")
    ap.add_argument("--replace-reviewed", action="store_true",
                    help="Back up and replace conflicting deployment files after review")
    args = ap.parse_args()
    target = args.target.resolve()
    if target == SOURCE or target.is_relative_to(SOURCE) or SOURCE.is_relative_to(target):
        raise ValueError("Keep the extracted package separate from the target checkout.")
    check = git(target, "rev-parse", "--show-toplevel")
    if check.returncode or Path(check.stdout.strip()).resolve() != target:
        raise ValueError("--target must be the root of an existing Git checkout.")
    missing = [f for f in REQUIRED if not safe_file(target, f).is_file()]
    if missing:
        raise ValueError("Application files are missing: " + ", ".join(missing))

    manifest_path = SOURCE / "deploy/import_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    entries = dict(manifest["files"])
    entries["deploy/import_manifest.json"] = digest(manifest_path)
    plan = []
    for relative, expected in sorted(entries.items()):
        if Path(relative).is_absolute() or any(x in (".git", ".env", ".env.admin") for x in Path(relative).parts):
            raise ValueError("Private or forbidden file in manifest: " + relative)
        src, dst = safe_file(SOURCE, relative), safe_file(target, relative)
        if not src.is_file() or digest(src) != expected:
            raise ValueError("Package file is incomplete or changed: " + relative)
        if dst.exists() and not dst.is_file():
            raise ValueError("Expected a file at: " + relative)
        state = "NEW" if not dst.exists() else ("SAME" if digest(dst) == expected else "REVIEW")
        plan.append((relative, state))
        print(f"{state:6} {relative}")

    patch = SOURCE / "deploy/patches/assignment2-existing-files.patch"
    patch_states = []
    for relative in PATCH_FILES:
        safe_file(target, relative)
        forward = git(target, "apply", "--check", "--include=" + relative, str(patch))
        if not forward.returncode:
            state = "APPLY"
        elif not git(target, "apply", "--reverse", "--check", "--include=" + relative, str(patch)).returncode:
            state = "ALREADY"
        else:
            state = "MANUAL"
        print(f"PATCH {state:7} {relative}")
        patch_states.append((relative, state))

    conflicts = [p for p, state in plan if state == "REVIEW"]
    manual = [p for p, state in patch_states if state == "MANUAL"]
    if not args.apply:
        print("\nPREVIEW ONLY. No target files were written.")
        print("Review REVIEW rows before using --replace-reviewed. MANUAL patches need a manual merge.")
        return 0
    if git(target, "status", "--porcelain").stdout.strip():
        raise ValueError("Save and commit your real current work first; the target working tree must be clean.")
    if manual:
        raise ValueError("No import applied. Manually review these patch conflicts first: " + ", ".join(manual))
    if conflicts and not args.replace_reviewed:
        raise ValueError("No import applied. Review conflicting deployment files; rerun with --replace-reviewed only after review.")

    backup = Path.home() / "EasyCampusStay_A2_Backups" / datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    changed = [(p, state) for p, state in plan if state != "SAME"]
    original = {p: (target / p).read_bytes() if (target / p).exists() else None for p, _ in changed}
    original.update({p: (target / p).read_bytes() for p, state in patch_states if state == "APPLY"})
    try:
        for relative, data in original.items():
            if data is not None:
                saved = backup / relative
                saved.parent.mkdir(parents=True, exist_ok=True)
                saved.write_bytes(data)
        for relative, _ in changed:
            dst = target / relative
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(SOURCE / relative, dst)
        for relative, state in patch_states:
            if state == "APPLY":
                result = git(target, "apply", "--include=" + relative, str(patch))
                if result.returncode:
                    raise ValueError("Could not apply compatible patch to " + relative + ": " + result.stderr)
    except Exception:
        for relative, data in original.items():
            dst = target / relative
            if data is None:
                dst.unlink(missing_ok=True)
            else:
                dst.parent.mkdir(parents=True, exist_ok=True)
                dst.write_bytes(data)
        raise
    print("\nImported reviewed deployment files and compatible patches.")
    if backup.exists():
        print("Existing changed files were backed up outside the repository at: " + str(backup))
    print("Your private .env, business-rule files and database data were not imported or replaced.")
    print("Next: git diff; Test-Path .\\deploy\\configure.py; then follow the configuration step.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError, KeyError) as exc:
        print("STOP: " + str(exc), file=sys.stderr)
        raise SystemExit(2)
