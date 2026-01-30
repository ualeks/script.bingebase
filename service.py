import time

import xbmc

from resources.lib.api import BingebaseAPI
from resources.lib.player import BingebasePlayer
from resources.lib.sync import do_sync
from resources.lib.utils import (
    get_setting, get_setting_bool, get_sync_interval_hours,
    log, log_debug, log_error, notify, reload_addon
)

POLL_INTERVAL = 300  # 5 minutes


class BingebaseMonitor(xbmc.Monitor):
    def __init__(self, service):
        super().__init__()
        self.service = service

    def onSettingsChanged(self):
        log_debug('Settings changed, reloading')
        reload_addon()
        self.service.reload_api()

    def onScanFinished(self, library):
        if library == 'video' and get_setting_bool('sync_on_library_update'):
            log('Library scan finished, triggering sync')
            self.service.trigger_sync()


class BingebaseService:
    def __init__(self):
        self.api = None
        self.player = None
        self.monitor = None
        self.last_sync_time = 0
        self._sync_requested = False

    def reload_api(self):
        webhook_url = get_setting('webhook_url')
        if webhook_url:
            self.api = BingebaseAPI(webhook_url)
            if self.player:
                self.player.api = self.api
        else:
            self.api = None

    def trigger_sync(self):
        self._sync_requested = True

    def _do_sync(self):
        if not self.api:
            log_debug('Skipping sync — webhook URL not configured')
            return
        try:
            do_sync(self.api)
            self.last_sync_time = time.time()
        except Exception as e:
            log_error('Sync error: {}'.format(str(e)))

    def _should_sync(self):
        if self._sync_requested:
            self._sync_requested = False
            return True

        interval_hours = get_sync_interval_hours()
        if interval_hours == 0:
            return False

        elapsed = time.time() - self.last_sync_time
        return elapsed >= (interval_hours * 3600)

    def run(self):
        log('Bingebase service starting')

        self.monitor = BingebaseMonitor(self)
        self.reload_api()

        if self.api:
            self.player = BingebasePlayer(self.api)
        else:
            self.player = BingebasePlayer(api=None)
            log('Webhook URL not configured — scrobbling disabled')

        # Sync on startup
        if get_setting_bool('sync_on_startup') and self.api:
            self._do_sync()

        # Main service loop
        while not self.monitor.abortRequested():
            if self._should_sync():
                self._do_sync()

            if self.monitor.waitForAbort(POLL_INTERVAL):
                break

        log('Bingebase service stopped')


if __name__ == '__main__':
    service = BingebaseService()
    service.run()
