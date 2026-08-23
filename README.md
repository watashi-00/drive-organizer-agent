# Google Drive Organizer Agent Toolkit

A small, agent-friendly toolkit for organizing Google Drive files.

The project is designed for workflows where a human authorizes Google Drive access, then an AI agent reads a Drive inventory and proposes or executes folder organization commands.

## What This MVP Does

- Lists Google Drive files and folders into a machine-readable JSON inventory.
- Creates folders and subfolders.
- Moves files or folders by Google Drive item ID.
- Provides a `SKILL.md` guide for AI agents that operate this project.
- Keeps authentication local through Google OAuth credentials.

This project is intentionally conservative: commands act on explicit Drive item IDs, not fuzzy file names, so an agent can make auditable plans before changing anything.

## Requirements

- Python 3.10+
- A Google Cloud OAuth client credentials file named `credentials.json`
- Google Drive API enabled in your Google Cloud project

## Google Setup

1. Go to Google Cloud Console.
2. Create or select a project.
3. Enable the **Google Drive API**.
4. Configure the OAuth consent screen.
5. If the OAuth consent screen uses the **External** user type, keep the app in **Testing** mode for personal/local use and add your own Google account under **Test users**. Google blocks external testing accounts that are not explicitly listed there.
6. In the OAuth consent screen scopes section, add this exact scope URL:

```text
https://www.googleapis.com/auth/drive
```

If the Google Cloud Console scope picker does not show it when searching for `drive`, paste the full URL above into the scope field. This project needs full Drive access because it lists existing files, creates folders, and moves files or folders across Drive locations.

7. Create an OAuth client ID for a **Desktop app**.
8. Download the OAuth client file.
9. Save it in this project root as:

```text
credentials.json
```

If Google shows "Access blocked" or says the app has not completed verification, confirm that:

- the app is still in **Testing** mode,
- your Google account is listed under **Test users** when the OAuth app user type is **External**,
- the exact scope `https://www.googleapis.com/auth/drive` is configured in the OAuth consent screen.

If the CLI returns `Google Drive API has not been used in project ... before or it is disabled`, enable the Google Drive API in the same Google Cloud project used by your `credentials.json`:

```text
https://console.developers.google.com/apis/api/drive.googleapis.com/overview
```

After enabling it, wait a few minutes and retry the command.

The first command that accesses Drive will open a browser authorization flow and create a local `token.json`.

Do not commit either file:

- `credentials.json`
- `token.json`

Both are ignored by `.gitignore`.

## Install

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

## Git Safety Hook

This repository includes an optional Git `pre-commit` hook that checks staged JSON files before a commit.

It blocks known local credential files such as `credentials.json` and `token.json`. If a staged JSON file looks like a Google Drive inventory, the hook asks for explicit confirmation before allowing the commit.

Git does not enable repository hooks automatically after clone. Install the hook once per clone:

```bash
drive-organizer-install-hooks
```

For intentional non-interactive commits that include Drive inventory JSON, set:

```bash
DRIVE_ORGANIZER_ALLOW_INVENTORY_JSON=1 git commit
```

## Basic Usage

Authorize and list your Drive:

```bash
drive-organizer list --output drive-inventory.json
```

Create a folder:

```bash
drive-organizer mkdir "Receipts"
```

Create a subfolder inside an existing folder:

```bash
drive-organizer mkdir "2026" --parent PARENT_FOLDER_ID
```

Move a file or folder:

```bash
drive-organizer move FILE_OR_FOLDER_ID DESTINATION_FOLDER_ID
```

Preview a move without changing Drive:

```bash
drive-organizer move FILE_OR_FOLDER_ID DESTINATION_FOLDER_ID --dry-run
```

## Agent Workflow

Recommended flow when using this with an AI agent:

1. Run `drive-organizer list --output drive-inventory.json`.
2. Give the agent access to `drive-inventory.json`, `README.md`, and `SKILL.md`.
3. Ask the agent to propose an organization plan.
4. Review the plan before execution.
5. Let the agent run explicit `mkdir` and `move` commands using Drive IDs.
6. Run `drive-organizer list --output drive-inventory-after.json` to verify the result.

## Inventory Format

The `list` command writes JSON with this shape:

```json
{
  "items": [
    {
      "id": "drive-item-id",
      "name": "Example.pdf",
      "mimeType": "application/pdf",
      "parents": ["parent-folder-id"],
      "webViewLink": "https://drive.google.com/...",
      "modifiedTime": "2026-08-23T12:00:00.000Z"
    }
  ]
}
```

Folders use this MIME type:

```text
application/vnd.google-apps.folder
```

## Safety Notes

- Prefer Drive IDs over names. Names are not unique in Google Drive.
- Use `--dry-run` before moves when building or testing an agent plan.
- Keep an inventory before and after a large organization pass.
- Start with a small folder or a limited query before applying broad changes.

## Useful Query Examples

List only folders:

```bash
drive-organizer list --query "mimeType = 'application/vnd.google-apps.folder'" --output folders.json
```

List files in one folder:

```bash
drive-organizer list --query "'FOLDER_ID' in parents" --output folder-items.json
```

List non-trashed PDF files:

```bash
drive-organizer list --query "mimeType = 'application/pdf' and trashed = false" --output pdfs.json
```

## Project Layout

```text
.
├── README.md
├── SKILL.md
├── githooks/
│   └── pre-commit
├── pyproject.toml
└── src/
    └── drive_organizer_agent/
        ├── __init__.py
        ├── cli.py
        ├── git_safety.py
        └── google_drive.py
```
