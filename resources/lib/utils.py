import xbmc
import xbmcaddon
import xbmcgui

ADDON = xbmcaddon.Addon()
ADDON_ID = ADDON.getAddonInfo('id')
ADDON_NAME = ADDON.getAddonInfo('name')


def get_setting(setting_id):
    return ADDON.getSetting(setting_id)


def get_setting_bool(setting_id):
    return ADDON.getSetting(setting_id).lower() == 'true'


def get_setting_int(setting_id):
    try:
        return int(ADDON.getSetting(setting_id))
    except (ValueError, TypeError):
        return 0


def set_setting(setting_id, value):
    ADDON.setSetting(setting_id, str(value))


def log(message, level=xbmc.LOGINFO):
    xbmc.log('[{}] {}'.format(ADDON_ID, message), level=level)


def log_debug(message):
    log(message, level=xbmc.LOGDEBUG)


def log_error(message):
    log(message, level=xbmc.LOGERROR)


def notify(message, icon=xbmcgui.NOTIFICATION_INFO, time=3000):
    xbmcgui.Dialog().notification(ADDON_NAME, message, icon, time)


def reload_addon():
    global ADDON
    ADDON = xbmcaddon.Addon()


# Sync interval mapping: setting index -> hours
SYNC_INTERVALS = {
    0: 0,   # Off
    1: 6,   # 6 hours
    2: 12,  # 12 hours
    3: 24,  # 24 hours
}


def get_sync_interval_hours():
    index = get_setting_int('sync_interval')
    return SYNC_INTERVALS.get(index, 24)


import json


def jsonrpc(method, params=None):
    request = {'jsonrpc': '2.0', 'method': method, 'id': 1}
    if params:
        request['params'] = params
    response = json.loads(xbmc.executeJSONRPC(json.dumps(request)))
    if 'error' in response:
        log_error('JSON-RPC error: {}'.format(response['error']))
        return None
    return response.get('result')


def get_show_uniqueids(episode_db_id):
    """Get the parent TV show's uniqueids for an episode."""
    # First get the tvshowid from the episode
    result = jsonrpc('VideoLibrary.GetEpisodeDetails', {
        'episodeid': episode_db_id,
        'properties': ['tvshowid'],
    })
    if not result or 'episodedetails' not in result:
        return {}

    tvshow_id = result['episodedetails'].get('tvshowid')
    if not tvshow_id:
        return {}

    # Then get the show's uniqueids
    result = jsonrpc('VideoLibrary.GetTVShowDetails', {
        'tvshowid': tvshow_id,
        'properties': ['uniqueid'],
    })
    if not result or 'tvshowdetails' not in result:
        return {}

    return result['tvshowdetails'].get('uniqueid', {})
