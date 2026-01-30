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
