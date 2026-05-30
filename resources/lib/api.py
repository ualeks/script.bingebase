import json
import time
from urllib.request import Request, urlopen
from urllib.parse import urlencode
from urllib.error import URLError, HTTPError

from resources.lib.utils import get_setting, log, log_error, BASE_URL

# Retry transient failures (network, 5xx). Import endpoint is idempotent
# server-side via total_watch_count dedup, so partial-progress retries
# don't double-write. Backoff keeps a thundering-herd impact low if
# the server is briefly overloaded mid-first-sync.
MAX_ATTEMPTS = 3
BACKOFF_SECONDS = (2, 5, 10)


class BingebaseAPI:
    def __init__(self):
        self.token = get_setting('access_token')
        self.webhook_url = get_setting('webhook_url')

    def _request(self, url, data=None, method=None, auth=True):
        headers = {
            'Content-Type': 'application/json',
            'User-Agent': 'Kodi/script.bingebase',
        }
        if auth and self.token:
            headers['Authorization'] = 'Bearer {}'.format(self.token)

        body = json.dumps(data).encode('utf-8') if data is not None else None
        last_exc = None

        for attempt in range(MAX_ATTEMPTS):
            req = Request(url, data=body, headers=headers, method=method)
            try:
                response = urlopen(req, timeout=120)
                response_body = response.read().decode('utf-8')
                if response_body:
                    return json.loads(response_body)
                return None
            except HTTPError as e:
                last_exc = e
                # 4xx is a permanent error — don't retry.
                if 400 <= e.code < 500:
                    log_error('HTTP error {} (not retrying)'.format(e.code))
                    raise
                log_error('HTTP error {} on attempt {}/{}'.format(e.code, attempt + 1, MAX_ATTEMPTS))
            except URLError as e:
                last_exc = e
                log_error('URL error on attempt {}/{}: {}'.format(attempt + 1, MAX_ATTEMPTS, e.reason))

            if attempt < MAX_ATTEMPTS - 1:
                delay = BACKOFF_SECONDS[attempt]
                log('Retrying in {}s'.format(delay))
                time.sleep(delay)

        raise last_exc

    def is_connected(self):
        return bool(self.token)

    def scrobble(self, payload):
        if not self.webhook_url:
            return None
        return self._request(self.webhook_url, data=payload, auth=False)

    def import_history(self, movies, episodes):
        url = '{}/api/v1/kodi/import'.format(BASE_URL)
        payload = {'movies': movies, 'episodes': episodes}
        return self._request(url, data=payload)

    def export_history(self, since=None):
        url = '{}/api/v1/kodi/export'.format(BASE_URL)
        if since:
            url += '?{}'.format(urlencode({'since': since}))
        return self._request(url)
