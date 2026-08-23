from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from drive_organizer_agent.google_drive import (
    DriveConfigurationError,
    DriveDependencyError,
    build_drive_service,
    create_folder,
    get_item,
    list_items,
    move_item,
)


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        return args.handler(args)
    except (DriveConfigurationError, DriveDependencyError) as error:
        print(f"Configuration error: {error}", file=sys.stderr)
        return 2
    except Exception as error:
        if error.__class__.__name__ != "HttpError":
            raise
        print(f"Google Drive API error: {error}", file=sys.stderr)
        return 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="drive-organizer",
        description="Agent-friendly Google Drive organization commands.",
    )
    subparsers = parser.add_subparsers(required=True)

    list_parser = subparsers.add_parser("list", help="Export Drive items as JSON.")
    list_parser.add_argument("--query", help="Google Drive API query. Defaults to non-trashed items.")
    list_parser.add_argument("--output", type=Path, help="Write JSON inventory to this file.")
    list_parser.add_argument("--page-size", type=int, default=1000, help="Drive API page size.")
    list_parser.set_defaults(handler=handle_list)

    mkdir_parser = subparsers.add_parser("mkdir", help="Create a Drive folder.")
    mkdir_parser.add_argument("name", help="Folder name to create.")
    mkdir_parser.add_argument("--parent", help="Optional parent folder ID.")
    mkdir_parser.set_defaults(handler=handle_mkdir)

    move_parser = subparsers.add_parser("move", help="Move a Drive item into a folder.")
    move_parser.add_argument("item_id", help="File or folder ID to move.")
    move_parser.add_argument("destination_folder_id", help="Destination folder ID.")
    move_parser.add_argument("--dry-run", action="store_true", help="Preview the move without changing Drive.")
    move_parser.set_defaults(handler=handle_move)

    return parser


def handle_list(args: argparse.Namespace) -> int:
    service = build_drive_service()
    items = list_items(service, query=args.query, page_size=args.page_size)
    payload = {"items": items}
    emit_json(payload, args.output)
    return 0


def handle_mkdir(args: argparse.Namespace) -> int:
    service = build_drive_service()
    folder = create_folder(service, args.name, parent_id=args.parent)
    emit_json(folder, None)
    return 0


def handle_move(args: argparse.Namespace) -> int:
    service = build_drive_service()

    if args.dry_run:
        item = get_item(service, args.item_id)
        destination = get_item(service, args.destination_folder_id)
        emit_json(
            {
                "dryRun": True,
                "item": item,
                "destination": destination,
                "command": {
                    "itemId": args.item_id,
                    "destinationFolderId": args.destination_folder_id,
                },
            },
            None,
        )
        return 0

    moved_item = move_item(service, args.item_id, args.destination_folder_id)
    emit_json(moved_item, None)
    return 0


def emit_json(payload: dict[str, Any], output: Path | None) -> None:
    rendered = json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True)
    if output:
        output.write_text(rendered + "\n", encoding="utf-8")
        print(f"Wrote {output}")
        return

    print(rendered)


if __name__ == "__main__":
    raise SystemExit(main())
