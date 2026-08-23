from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

KNOWN_SECRET_JSON_NAMES = {
    "credentials.json",
    "token.json",
    "client_secret.json",
}

INVENTORY_FILENAME_MARKERS = {
    "inventory",
    "drive-",
}

DRIVE_ITEM_KEYS = {
    "id",
    "name",
    "mimeType",
    "parents",
    "webViewLink",
}

DRIVE_CONTENT_MARKERS = (
    "application/vnd.google-apps.folder",
    "drive.google.com",
    "docs.google.com",
    "emailAddress",
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Git safety checks for Drive inventory files.")
    subparsers = parser.add_subparsers(required=True)

    pre_commit_parser = subparsers.add_parser("pre-commit")
    pre_commit_parser.set_defaults(handler=handle_pre_commit)

    install_parser = subparsers.add_parser("install-hooks")
    install_parser.set_defaults(handler=handle_install_hooks)

    args = parser.parse_args(argv)
    return args.handler(args)


def pre_commit_main() -> int:
    return handle_pre_commit(argparse.Namespace())


def install_hooks_main() -> int:
    return handle_install_hooks(argparse.Namespace())


def handle_pre_commit(_: argparse.Namespace) -> int:
    repo_root = get_repo_root()
    staged_json_files = get_staged_json_files(repo_root)
    if not staged_json_files:
        return 0

    secret_files = [path for path in staged_json_files if path.name in KNOWN_SECRET_JSON_NAMES]
    if secret_files:
        print("Refusing to commit known local credential/token JSON files:", file=sys.stderr)
        for path in secret_files:
            print(f"  - {path}", file=sys.stderr)
        print("Remove them from the index before committing.", file=sys.stderr)
        return 1

    inventory_files = [path for path in staged_json_files if looks_like_drive_inventory(repo_root / path)]
    if not inventory_files:
        return 0

    print("Potential Google Drive inventory JSON detected in staged files:", file=sys.stderr)
    for path in inventory_files:
        print(f"  - {path}", file=sys.stderr)

    if os.environ.get("DRIVE_ORGANIZER_ALLOW_INVENTORY_JSON") == "1":
        print("Continuing because DRIVE_ORGANIZER_ALLOW_INVENTORY_JSON=1 is set.", file=sys.stderr)
        return 0

    answer = prompt_user_confirmation("These files may expose Drive metadata. Continue with commit? [y/N] ")
    if answer is None:
        print(
            "Commit blocked in a non-interactive shell. Set "
            "DRIVE_ORGANIZER_ALLOW_INVENTORY_JSON=1 to override intentionally.",
            file=sys.stderr,
        )
        return 1

    if answer.strip().lower() in {"y", "yes"}:
        return 0

    print("Commit cancelled.", file=sys.stderr)
    return 1


def prompt_user_confirmation(prompt: str) -> str | None:
    # 1. POSIX systems (Linux, macOS, Git Bash)
    try:
        with open("/dev/tty", "w", encoding="utf-8") as tty_out, open("/dev/tty", "r", encoding="utf-8") as tty_in:
            tty_out.write(prompt)
            tty_out.flush()
            return tty_in.readline()
    except Exception:
        pass

    # 2. Windows native console (CMD / PowerShell / Windows Terminal)
    if sys.platform == "win32":
        try:
            with open("CONOUT$", "w", encoding="utf-8") as conout, open("CONIN$", "r", encoding="utf-8") as conin:
                conout.write(prompt)
                conout.flush()
                return conin.readline()
        except Exception:
            pass

    # 3. Fallback to sys.stdin if it's a TTY
    if sys.stdin.isatty():
        try:
            return input(prompt)
        except EOFError:
            return None

    return None



def handle_install_hooks(_: argparse.Namespace) -> int:
    repo_root = get_repo_root()
    hooks_dir = repo_root / "githooks"
    pre_commit = hooks_dir / "pre-commit"
    if not pre_commit.exists():
        print(f"Missing hook file: {pre_commit}", file=sys.stderr)
        return 1

    subprocess.run(["git", "config", "core.hooksPath", "githooks"], cwd=repo_root, check=True)
    pre_commit.chmod(pre_commit.stat().st_mode | 0o111)
    print("Installed repository Git hooks via core.hooksPath=githooks.")
    return 0


def get_repo_root() -> Path:
    result = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"],
        check=True,
        capture_output=True,
        text=True,
    )
    return Path(result.stdout.strip())


def get_staged_json_files(repo_root: Path) -> list[Path]:
    result = subprocess.run(
        ["git", "diff", "--cached", "--name-only", "--diff-filter=ACMR", "--", "*.json"],
        cwd=repo_root,
        check=True,
        capture_output=True,
        text=True,
    )
    return [Path(line) for line in result.stdout.splitlines() if line.strip()]


def looks_like_drive_inventory(path: Path) -> bool:
    lower_name = path.name.lower()
    if any(marker in lower_name for marker in INVENTORY_FILENAME_MARKERS):
        return True

    try:
        raw = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return False

    if any(marker in raw for marker in DRIVE_CONTENT_MARKERS):
        return True

    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        return False

    return contains_drive_item_shape(payload)


def contains_drive_item_shape(value: Any) -> bool:
    if isinstance(value, dict):
        if DRIVE_ITEM_KEYS.issubset(value.keys()):
            return True
        return any(contains_drive_item_shape(child) for child in value.values())

    if isinstance(value, list):
        return any(contains_drive_item_shape(child) for child in value)

    return False


if __name__ == "__main__":
    raise SystemExit(main())
