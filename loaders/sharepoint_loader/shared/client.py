import requests
from io import BytesIO
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


def _session_with_retries() -> requests.Session:
    session = requests.Session()
    retry = Retry(
        total=5,
        backoff_factor=1,          # 1s, 2s, 4s, 8s, 16s
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET", "POST"],
        raise_on_status=False,
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("https://", adapter)
    return session


class SharePointClient:
    def __init__(self, tenant_id: str, client_id: str, client_secret: str, site_url: str):
        self.tenant_id = tenant_id
        self.client_id = client_id
        self.client_secret = client_secret
        self.site_url = site_url
        self.access_token = None
        self._site_id = None
        self._drive_id = None

    @classmethod
    def from_config(cls, config: dict) -> "SharePointClient":
        """Build a client from SHAREPOINT_CONFIG, validating required credentials."""
        tenant = config.get("sharepoint_tenant_id")
        cid = config.get("sharepoint_client_id")
        secret = config.get("sharepoint_client_secret")
        site = config.get("sharepoint_site_url")
        missing = [k for k, v in (
            ("SHAREPOINT_TENANT_ID", tenant), ("SHAREPOINT_CLIENT_ID", cid),
            ("SHAREPOINT_CLIENT_SECRET", secret), ("SHAREPOINT_SITE_URL", site),
        ) if not v]
        if missing:
            raise RuntimeError("Missing SharePoint credentials: " + ", ".join(missing))
        return cls(tenant_id=tenant, client_id=cid, client_secret=secret, site_url=site)

    def authenticate(self):
        token_url = f"https://login.microsoftonline.com/{self.tenant_id}/oauth2/v2.0/token"
        data = {
            "grant_type": "client_credentials",
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "scope": "https://graph.microsoft.com/.default",
        }
        session = _session_with_retries()
        resp = session.post(token_url, data=data)
        resp.raise_for_status()
        self.access_token = resp.json().get("access_token")
        self._session = session
        return self.access_token

    def _get(self, url: str, **kwargs) -> requests.Response:
        if not hasattr(self, "_session") or self._session is None:
            self._session = _session_with_retries()
        resp = self._session.get(url, headers=self._get_headers(), **kwargs)
        resp.raise_for_status()
        return resp

    def _get_headers(self) -> dict:
        if not self.access_token:
            raise RuntimeError("No access token — call authenticate() first")
        return {"Authorization": f"Bearer {self.access_token}"}

    def get_site_id(self) -> str:
        if self._site_id:
            return self._site_id
        # Resolve the site by its site collection path
        # Expecting site_url like https://<tenant>.sharepoint.com/sites/<SiteName>
        resp = self._get(f"https://graph.microsoft.com/v1.0/sites?search={self.site_url}")
        results = resp.json().get("value", [])
        if not results:
            from urllib.parse import urlparse
            parsed = urlparse(self.site_url)
            url = f"https://graph.microsoft.com/v1.0/sites/{parsed.hostname}:{parsed.path}"
            resp = self._get(url)
            self._site_id = resp.json().get("id")
            return self._site_id
        self._site_id = results[0].get("id")
        return self._site_id

    def get_drive_id(self, site_id: str) -> str:
        if self._drive_id:
            return self._drive_id
        resp = self._get(f"https://graph.microsoft.com/v1.0/sites/{site_id}/drive")
        self._drive_id = resp.json().get("id")
        return self._drive_id

    def get_download_url(self, file_path: str) -> str:
        """Retourne l'URL de téléchargement direct (Azure Blob SAS) sans télécharger le contenu."""
        site_id = self.get_site_id()
        drive_id = self.get_drive_id(site_id)
        encoded_path = file_path.lstrip("/")
        url = f"https://graph.microsoft.com/v1.0/drives/{drive_id}/root:/{encoded_path}:/content"
        resp = self._session.get(url, headers=self._get_headers(), allow_redirects=False)
        if resp.status_code in (301, 302, 303, 307, 308):
            return resp.headers["Location"]
        return url

    def download_file(self, file_path: str) -> BytesIO:
        site_id = self.get_site_id()
        drive_id = self.get_drive_id(site_id)
        encoded_path = file_path.lstrip("/")
        url = f"https://graph.microsoft.com/v1.0/drives/{drive_id}/root:/{encoded_path}:/content"
        response = self._get(url)
        print(f"✓ File downloaded: {file_path}")
        return BytesIO(response.content)

    def list_files(self, folder_path: str = "/") -> list:
        site_id = self.get_site_id()
        drive_id = self.get_drive_id(site_id)
        if folder_path == "/":
            url = f"https://graph.microsoft.com/v1.0/drives/{drive_id}/root/children"
        else:
            encoded_path = folder_path.lstrip("/")
            url = f"https://graph.microsoft.com/v1.0/drives/{drive_id}/root:/{encoded_path}:/children"
        return self._get(url).json().get("value", [])
