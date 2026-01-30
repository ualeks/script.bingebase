import json
from urllib.request import Request, urlopen
from urllib.parse import urlencode, urlparse
from urllib.error import URLError, HTTPError

from resources.lib.utils import log, log_debug, log_error


class BingebaseAPI:
    def __init__(self, webhook_url):
        self.webhook_url = webhook_url.rstrip('/')
        parsed = urlparse(self.webhook_url)
        self.base_url = '{}://{}'.format(parsed.scheme, parsed.netloc)

    def _request(self, url, data=None, method=None):
        headers = {'Content-Type': 'application/json', 'User-Agent': 'Kodi/script.bingebase'}
        body = json.dumps(data).encode('utf-8') if data is not None else None
        req = Request(url, data=body, headers=headers, method=method)
        try:
            response = urlopen(req, timeout=30)
            response_body = response.read().decode('utf-8')
            if response_body:
                return json.loads(response_body)
            return None
        except HTTPError as e:
            log_error('HTTP error {}: {} - {}'.format(e.code, url, e.read().decode('utf-8', errors='replace')))
            raise
        except URLError as e:
            log_error('URL error: {} - {}'.format(url, e.reason))
            raise

    def test_connection(self):
        try:
            req = Request(self.webhook_url, method='HEAD')
            req.add_header('User-Agent', 'Kodi/script.bingebase')
            urlopen(req, timeout=10)
            return True
        except HTTPError as e:
            # 405 Method Not Allowed is acceptable for HEAD — endpoint exists
            if e.code == 405:
                return True
            log_error('Test connection failed: HTTP {}'.format(e.code))
            return False
        except URLError as e:
            log_error('Test connection failed: {}'.format(e.reason))
            return False

    def scrobble(self, payload):
        log_debug('Scrobbling: {}'.format(json.dumps(payload)))
        return self._request(self.webhook_url, data=payload)

    def import_history(self, movies, episodes):
        url = '{}/api/v1/kodi/import'.format(self.base_url)
        payload = {'movies': movies, 'episodes': episodes}
        log('Importing {} movies, {} episodes to Bingebase'.format(len(movies), len(episodes)))
        return self._request(url, data=payload)

    def export_history(self, since=None):
        url = '{}/api/v1/kodi/export'.format(self.base_url)
        if since:
            url += '?{}'.format(urlencode({'since': since}))
        log('Fetching watch history from Bingebase')
        return self._request(url)
