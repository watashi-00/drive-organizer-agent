from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

FOLDER_MIME_TYPE = "application/vnd.google-apps.folder"
SCOPES = ["https://www.googleapis.com/auth/drive"]


@dataclass(frozen=True)
class DrivePaths:
    credentials: Path = Path("credentials.json")
    token: Path = Path("token.json")


class DriveConfigurationError(RuntimeError):
    """Raised when local Google Drive OAuth files are missing or invalid."""


class DriveDependencyError(RuntimeError):
    """Raised when Google Drive client dependencies are not installed."""


def build_drive_service(paths: DrivePaths | None = None) -> Any:
    try:
        from googleapiclient.discovery import build
    except ModuleNotFoundError as error:
        raise DriveDependencyError(
            "Missing Google Drive dependencies. Run `pip install -e .` from the project root."
        ) from error

    selected_paths = paths or DrivePaths()
    credentials = _load_credentials(selected_paths)
    return build("drive", "v3", credentials=credentials)


def _load_credentials(paths: DrivePaths) -> Any:
    try:
        from google.auth.transport.requests import Request
        from google.oauth2.credentials import Credentials
        from google_auth_oauthlib.flow import InstalledAppFlow
    except ModuleNotFoundError as error:
        raise DriveDependencyError(
            "Missing Google Drive dependencies. Run `pip install -e .` from the project root."
        ) from error

    credentials: Any = None

    if paths.token.exists():
        credentials = Credentials.from_authorized_user_file(str(paths.token), SCOPES)

    if credentials and credentials.valid:
        return credentials

    if credentials and credentials.expired and credentials.refresh_token:
        credentials.refresh(Request())
        paths.token.write_text(credentials.to_json(), encoding="utf-8")
        return credentials

    if not paths.credentials.exists():
        raise DriveConfigurationError(
            "Missing credentials.json. Create a Google Cloud OAuth Desktop client, "
            "download it, and save it as credentials.json in the project root."
        )

    flow = InstalledAppFlow.from_client_secrets_file(str(paths.credentials), SCOPES)
    credentials = flow.run_local_server(port=0)
    paths.token.write_text(credentials.to_json(), encoding="utf-8")
    return credentials


def list_items(service: Any, query: str | None = None, page_size: int = 1000) -> list[dict[str, Any]]:
    drive_query = query or "trashed = false"
    fields = (
        "nextPageToken, "
        "files(id, name, mimeType, parents, webViewLink, modifiedTime, size, owners(displayName,emailAddress))"
    )
    items: list[dict[str, Any]] = []
    page_token: str | None = None

    while True:
        response = (
            service.files()
            .list(
                q=drive_query,
                spaces="drive",
                fields=fields,
                pageSize=page_size,
                pageToken=page_token,
            )
            .execute()
        )
        items.extend(response.get("files", []))
        page_token = response.get("nextPageToken")
        if not page_token:
            return items


def create_folder(service: Any, name: str, parent_id: str | None = None) -> dict[str, Any]:
    metadata: dict[str, Any] = {
        "name": name,
        "mimeType": FOLDER_MIME_TYPE,
    }
    if parent_id:
        metadata["parents"] = [parent_id]

    return (
        service.files()
        .create(body=metadata, fields="id, name, mimeType, parents, webViewLink")
        .execute()
    )


def get_item(service: Any, item_id: str) -> dict[str, Any]:
    return (
        service.files()
        .get(fileId=item_id, fields="id, name, mimeType, parents, webViewLink")
        .execute()
    )


def move_item(service: Any, item_id: str, destination_folder_id: str) -> dict[str, Any]:
    item = get_item(service, item_id)
    previous_parents = ",".join(item.get("parents", []))

    request = service.files().update(
        fileId=item_id,
        addParents=destination_folder_id,
        removeParents=previous_parents or None,
        fields="id, name, mimeType, parents, webViewLink",
    )

    return request.execute()
