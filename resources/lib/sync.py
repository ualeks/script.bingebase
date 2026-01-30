import json
import time

import xbmc

from resources.lib.utils import (
    get_setting_bool, set_setting, log, log_debug, log_error, notify
)


def _jsonrpc(method, params=None):
    request = {'jsonrpc': '2.0', 'method': method, 'id': 1}
    if params:
        request['params'] = params
    response = json.loads(xbmc.executeJSONRPC(json.dumps(request)))
    if 'error' in response:
        log_error('JSON-RPC error: {}'.format(response['error']))
        return None
    return response.get('result')


def get_watched_movies():
    result = _jsonrpc('VideoLibrary.GetMovies', {
        'filter': {'field': 'playcount', 'operator': 'greaterthan', 'value': '0'},
        'properties': ['title', 'year', 'playcount', 'lastplayed', 'uniqueid'],
    })
    if result and 'movies' in result:
        return result['movies']
    return []


def get_watched_episodes():
    result = _jsonrpc('VideoLibrary.GetEpisodes', {
        'filter': {'field': 'playcount', 'operator': 'greaterthan', 'value': '0'},
        'properties': ['title', 'showtitle', 'season', 'episode', 'playcount', 'lastplayed', 'uniqueid'],
    })
    if result and 'episodes' in result:
        return result['episodes']
    return []


def get_all_movies():
    result = _jsonrpc('VideoLibrary.GetMovies', {
        'properties': ['title', 'year', 'playcount', 'uniqueid'],
    })
    if result and 'movies' in result:
        return result['movies']
    return []


def get_all_episodes():
    result = _jsonrpc('VideoLibrary.GetEpisodes', {
        'properties': ['title', 'showtitle', 'season', 'episode', 'playcount', 'uniqueid'],
    })
    if result and 'episodes' in result:
        return result['episodes']
    return []


def _format_movie_for_import(movie):
    return {
        'title': movie.get('title', ''),
        'year': movie.get('year', 0),
        'playcount': movie.get('playcount', 1),
        'lastplayed': movie.get('lastplayed', ''),
        'uniqueIds': movie.get('uniqueid', {}),
    }


def _format_episode_for_import(episode):
    return {
        'title': episode.get('title', ''),
        'tvShowTitle': episode.get('showtitle', ''),
        'season': episode.get('season', 0),
        'episode': episode.get('episode', 0),
        'playcount': episode.get('playcount', 1),
        'lastplayed': episode.get('lastplayed', ''),
        'uniqueIds': episode.get('uniqueid', {}),
    }


def import_kodi_to_bingebase(api):
    movies = get_watched_movies()
    episodes = get_watched_episodes()

    formatted_movies = [_format_movie_for_import(m) for m in movies]
    formatted_episodes = [_format_episode_for_import(e) for e in episodes]

    if not formatted_movies and not formatted_episodes:
        log('Nothing to import — no watched items in Kodi library')
        return 0, 0

    api.import_history(formatted_movies, formatted_episodes)
    log('Imported {} movies, {} episodes to Bingebase'.format(len(formatted_movies), len(formatted_episodes)))
    return len(formatted_movies), len(formatted_episodes)


def _find_kodi_item(kodi_items, uniqueids, id_key='movieid'):
    for item in kodi_items:
        kodi_uids = item.get('uniqueid', {})
        for id_type in ('tmdb', 'tvdb', 'imdb'):
            bingebase_id = str(uniqueids.get(id_type, ''))
            kodi_id = str(kodi_uids.get(id_type, ''))
            if bingebase_id and kodi_id and bingebase_id == kodi_id:
                return item
    return None


def export_bingebase_to_kodi(api, since=None):
    data = api.export_history(since=since)
    if not data:
        log('No new watch history from Bingebase')
        return 0

    kodi_movies = get_all_movies()
    kodi_episodes = get_all_episodes()
    marked_count = 0

    for movie in data.get('movies', []):
        match = _find_kodi_item(kodi_movies, movie.get('uniqueIds', {}), id_key='movieid')
        if match and match.get('playcount', 0) == 0:
            _jsonrpc('VideoLibrary.SetMovieDetails', {
                'movieid': match['movieid'],
                'playcount': 1,
            })
            log_debug('Marked movie as watched: {}'.format(match.get('title', '')))
            marked_count += 1

    for episode in data.get('episodes', []):
        match = _find_kodi_item(kodi_episodes, episode.get('uniqueIds', {}), id_key='episodeid')
        if match and match.get('playcount', 0) == 0:
            _jsonrpc('VideoLibrary.SetEpisodeDetails', {
                'episodeid': match['episodeid'],
                'playcount': 1,
            })
            log_debug('Marked episode as watched: {} S{:02d}E{:02d}'.format(
                match.get('showtitle', ''), match.get('season', 0), match.get('episode', 0)
            ))
            marked_count += 1

    log('Marked {} items as watched in Kodi'.format(marked_count))
    return marked_count


def do_sync(api):
    log('Starting sync...')
    notify('Syncing...')

    movie_count = 0
    episode_count = 0
    marked_count = 0

    try:
        if get_setting_bool('sync_kodi_to_bingebase'):
            movie_count, episode_count = import_kodi_to_bingebase(api)

        last_sync = _get_last_sync_timestamp()

        if get_setting_bool('sync_bingebase_to_kodi'):
            marked_count = export_bingebase_to_kodi(api, since=last_sync)

        _save_last_sync_timestamp()

        log('Sync complete: {} movies, {} episodes imported; {} items marked watched'.format(
            movie_count, episode_count, marked_count
        ))
        notify('Sync complete: {} movies, {} episodes'.format(movie_count, episode_count))

    except Exception as e:
        log_error('Sync failed: {}'.format(str(e)))
        notify('Sync failed', icon=xbmc.NOTIFICATION_ERROR)


def _get_last_sync_timestamp():
    from resources.lib.utils import get_setting
    ts = get_setting('last_sync_timestamp')
    return ts if ts else None


def _save_last_sync_timestamp():
    ts = time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())
    set_setting('last_sync_timestamp', ts)
