import os
import re
from datetime import datetime, timedelta
from io import BytesIO

from loaders.sharepoint_loader.shared.client import SharePointClient


# Target SharePoint folders
PATH_DONNEES_SOURCE = "09_DATA/AA_Public/03_Reporting/Business/Suivis/reporting hebdo/Données sources"
PATH_REPORTING_MENSUEL = "09_DATA/AA_Public/03_Reporting/Business/Suivis/reporting mensuel"

_FILENAME_RE = re.compile(r"^donnees_source_(\d{4})_(\d{2})_(\d{2})(?:_(\d{2})(\d{2})(\d{2}))?\.xlsx$")


def _parse_filename_date(name: str) -> datetime | None:
    """Extract the timestamp embedded in a donnees_source_*.xlsx filename, or None if it doesn't match."""
    m = _FILENAME_RE.match(name)
    if not m:
        return None
    year, month, day, hour, minute, second = m.groups()
    return datetime(
        int(year), int(month), int(day),
        int(hour or 0), int(minute or 0), int(second or 0),
    )


def _get_client() -> SharePointClient:
    client = SharePointClient(
        tenant_id=os.environ["SHAREPOINT_TENANT_ID"],
        client_id=os.environ["SHAREPOINT_CLIENT_ID"],
        client_secret=os.environ["SHAREPOINT_CLIENT_SECRET"],
        site_url=os.environ["SHAREPOINT_SITE_URL"],
    )
    client.authenticate()
    return client


def _release_lock(client: SharePointClient, drive_id: str, upload_path: str) -> None:
    """Try to release a SharePoint file lock (checked-out state) before uploading."""
    item_url = f"https://graph.microsoft.com/v1.0/drives/{drive_id}/root:/{upload_path}"
    get_resp = client._session.get(item_url, headers=client._get_headers())
    if get_resp.status_code != 200:
        return  # File does not exist yet, nothing to unlock

    item_id = get_resp.json().get("id")
    if not item_id:
        return

    base = f"https://graph.microsoft.com/v1.0/drives/{drive_id}/items/{item_id}"
    headers = {**client._get_headers(), "Content-Type": "application/json"}

    # Try discardCheckout first (releases a SharePoint checked-out lock immediately)
    discard_resp = client._session.post(f"{base}/discardCheckout", headers=headers)
    if discard_resp.status_code in (200, 204):
        print("Lock released via discardCheckout")
        return

    # Fall back to checkin (publishes the checked-out version and releases the lock)
    checkin_resp = client._session.post(
        f"{base}/checkin",
        headers=headers,
        json={"comment": "", "checkInAs": "published"},
    )
    if checkin_resp.status_code in (200, 204):
        print("Lock released via checkin")
    else:
        print(f"Warning: could not release lock ({checkin_resp.status_code})")


def download_previous_donnees_source(days_back: int = 14) -> BytesIO | None:
    """Download the donnees_source_*.xlsx closest to (but not more recent than) `days_back` days ago.

    Selects by the date embedded in the filename, not by position in the file listing —
    ad-hoc/manual runs (workflow_dispatch) can upload several files within the same week,
    so "the 2nd most recent file" does not reliably mean "2 weeks ago". Defaults to 14 days
    (S-2) to match the "Ecart vs S-2" recap column.
    """
    client = _get_client()
    files = client.list_files(PATH_DONNEES_SOURCE)
    dated = sorted(
        (dt, f["name"]) for f in files
        if (dt := _parse_filename_date(f.get("name", ""))) is not None
    )
    if not dated:
        return None

    cutoff = datetime.now() - timedelta(days=days_back)
    candidates = [d for d in dated if d[0] <= cutoff]
    if not candidates:
        print(f"No donnees_source file older than {days_back} days on SharePoint.")
        return None

    _, filename = candidates[-1]
    print(f"Using {filename} as S-2 reference for the écart calculation.")
    return client.download_file(f"{PATH_DONNEES_SOURCE}/{filename}")


def upload_to_sharepoint(content: BytesIO, filename: str, folder_path: str) -> None:
    """Upload an Excel file to a SharePoint folder."""
    client = _get_client()
    site_id = client.get_site_id()
    drive_id = client.get_drive_id(site_id)

    upload_path = f"{folder_path}/{filename}"

    # Release any existing checkout lock before uploading
    _release_lock(client, drive_id, upload_path)

    # Create an upload session — works even when the file exists
    create_session_url = (
        f"https://graph.microsoft.com/v1.0/drives/{drive_id}/root:/{upload_path}:/createUploadSession"
    )
    session_resp = client._session.post(
        create_session_url,
        headers={**client._get_headers(), "Content-Type": "application/json"},
        json={"item": {"@microsoft.graph.conflictBehavior": "replace"}},
    )
    session_resp.raise_for_status()
    upload_url = session_resp.json()["uploadUrl"]

    file_data = content.read()
    file_size = len(file_data)
    resp = client._session.put(
        upload_url,
        headers={
            "Content-Length": str(file_size),
            "Content-Range": f"bytes 0-{file_size - 1}/{file_size}",
            "Content-Type": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        },
        data=file_data,
    )
    resp.raise_for_status()
    print(f"Uploaded {filename} to SharePoint: {upload_path}")
