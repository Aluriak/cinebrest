

import requests
import json
import time
import bs4
import re

CACHE_FILE = 'cache.json'
REGEX_HOUR = re.compile(r"([0-9]{1,2})[hH:]([0-9]{0,2})[mM]?")

def now_in_year_month_day(type_=int) -> (int, int, int) or str:
    now = time.localtime(time.time())
    if type_ is str:
        return f"{now.tm_year}-{now.tm_mon:02d}-{now.tm_mday:02d}"
    else:
        return now.tm_year, now.tm_mon, now.tm_mday

def now_in_hour_and_minutes(type_=int) -> (int, int) or str:
    now = time.localtime(time.time())
    if type_ is str:
        return f"{now.tm_hour:02d}h{now.tm_min:02d}"
    else:
        return now.tm_hour, now.tm_min

def is_in_the_future(given_hour: str) -> bool:
    match = REGEX_HOUR.fullmatch(given_hour)
    if match:
        given_hour, given_minute = match.groups()
        given_hour = int(given_hour)
        given_minute = int(given_minute or 0)
    else:
        print(f"Given hour {repr(given_hour)} is not a valid hour representation. Regex is {repr(REGEX_HOUR)}.")
        return False
    hour, minute = now_in_hour_and_minutes()
    ok = (given_hour > hour) or (given_hour == hour and given_minute > minute)
    # print(f'COMPARE {given_hour}h{given_minute} with {hour}h{minute}: {ok}')
    return ok



def load_cache() -> dict:
    try:
        with open(CACHE_FILE) as fd:
            return json.loads(fd.read()) or {}
    except FileNotFoundError:
        print("Cache file doesn't exists. Empty cache is created.")
        return {}

def save_cache() -> dict:
    with open(CACHE_FILE, 'w') as fd:
        json.dump(CACHE, fd, indent=4)
    return CACHE



def get_page(url: str, html=True, session=None) -> bs4.BeautifulSoup:
    if html:
        parser = lambda url: bs4.BeautifulSoup(CACHE[url], features='html.parser')
    else:
        parser = lambda url: json.loads(CACHE[url])
    if url in CACHE:
        return parser(url)
    print(f'poking at {url}')
    CACHE[url] = (session or requests).get(url).text
    return parser(url)

def parse_les_studios(*, URL='https://www.cine-studios.fr/films-a-l-affiche/') -> [dict]:
    soup = get_page(URL)
    for elm in soup.find_all(**{'class': 'btn bt-film-small bthorai'}):
        url = elm['href']
        soup = get_page(url)
        todays = tuple(soup.find_all('td', **{'class': 'today'}))
        assert len(todays) == 1, todays
        todays = tuple((hour, '?') for hour in (str(elm.text).strip() for elm in todays[0]) if hour)
        yield {
            'title': next(iter(soup.find_all('h3', **{'class': 'fn'}))).text,
            'desc': next(iter(soup.find_all('p', **{'class': 'synopsis'}))).text,
            'today': todays,
            'ok': tuple((hour, kind) for hour, kind in todays if is_in_the_future(hour)),
            'where': 'Les Studios',
        }


def parse_paté_gaumont() -> [dict]:
    with requests.Session() as sss:
        all_shows = {
            show['slug']: show
            for show in get_page('https://www.cinemaspathegaumont.com/api/shows?language=fr', html=False, session=sss)['shows']
        }
        data = get_page('https://www.cinemaspathegaumont.com/api/zone/brest?language=fr', html=False, session=sss)['shows']
        for movie in data:
            if movie['slug'] not in all_shows or all_shows[movie['slug']]['next24ShowtimesCount'] == 0:
                continue  # that film will not interest us
            # print(movie)
            # print(all_shows[movie['slug']])
            # print()
            url = f"https://www.cinemaspathegaumont.com/api/show/{movie['slug']}"
            movie_metadata = get_page(url, html=False, session=sss)
            if 'slug' not in movie_metadata:
                continue  # that film isn't even out
            url = f"https://www.cinemaspathegaumont.com/api/show/{movie['slug']}/showtimes/cinema-multiplexe-liberte/{now_in_year_month_day(str)}"
            hour_data = get_page(url, html=False, session=sss)
            # print(hour_data)
            todays = tuple(
                ('h'.join(shift['time'].split()[1].split(':')[:-1]), shift['version'])
                for shift in hour_data
                if isinstance(shift, dict) and shift['status'] == 'available'
            )
            yield {
                'title': movie_metadata['title'],
                'desc': movie_metadata['synopsis'],
                'today': todays,
                'ok': todays,
                'where': 'Multiplexe Liberté',
            }


CACHE = {}
def parse_all():
    global CACHE
    CACHE = load_cache()
    save_cache()
    print(f"{len(CACHE)} pages cached")
    yield from parse_les_studios()
    yield from parse_paté_gaumont()
    save_cache()
