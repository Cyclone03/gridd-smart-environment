import json
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from .errors import HttpRequestError


def fetch_json(url: str, *, timeout: float) -> object:
    request = Request(url, headers={"Accept": "application/json"})
    try:
        with urlopen(request, timeout=timeout) as response:
            if not 200 <= response.status < 300:
                raise HttpRequestError(f"HTTP request failed with status {response.status}.",
                                       status_code=response.status)
            return json.loads(response.read())
    except HTTPError as exc:
        raise HttpRequestError(f"HTTP request failed with status {exc.code}.",
                               status_code=exc.code) from exc
    except (URLError, TimeoutError) as exc:
        raise HttpRequestError("HTTP request could not be completed.") from exc
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise HttpRequestError("The response did not contain valid JSON.") from exc
