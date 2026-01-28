import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

_session = None

def get_session():
    global _session
    if not _session:
        _session = requests.Session()
        retry = Retry(total=3, backoff_factor=1, status_forcelist=[429, 500, 502, 503, 504])
        _session.mount("http://", HTTPAdapter(max_retries=retry))
        _session.mount("https://", HTTPAdapter(max_retries=retry))
    return _session

def download(url, timeout=30):
    try:
        r = get_session().get(url, timeout=timeout)
        r.raise_for_status()
        return r.content
    except requests.exceptions.SSLError:
        try:
            r = get_session().get(url, timeout=timeout, verify=False)
            r.raise_for_status()
            return r.content
        except:
            return None
    except:
        return None
