

import requests
import datetime
import json
import bs4
import re

CACHE_FILE = 'cache.json'
REGEX_HOUR = re.compile(r"([0-9]{1,2})[hH:]([0-9]{0,2})[mM]?")
DIFF_TO_MATCH_BREST_ON_THAT_SERVER = datetime.timedelta(seconds=2697)  # yes that's dirty. Please explain to me how to do that properly.

def now_in_year_month_day(type_=int) -> (int, int, int) or str:
    now = datetime.datetime.now() - DIFF_TO_MATCH_BREST_ON_THAT_SERVER
    if type_ is str:
        return f"{now.year}-{now.month:02d}-{now.day:02d}"
    else:
        return now.year, now.month, now.day

def now_in_hour_and_minutes(type_=int) -> (int, int) or str:
    now = datetime.datetime.now() - DIFF_TO_MATCH_BREST_ON_THAT_SERVER
    if type_ is str:
        return f"{now.hour:02d}h{now.minute:02d}"
    else:
        return now.hour, now.minute

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
        todays = tuple((hour, 'VO?') for hour in (str(elm.text).strip() for elm in todays[0]) if hour)
        yield {
            'title': next(iter(soup.find_all('h3', **{'class': 'fn'}))).text,
            'synopsis': next(iter(soup.find_all('p', **{'class': 'synopsis'}))).text,
            'today': todays,
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
                'synopsis': movie_metadata['synopsis'],
                'today': todays,
                'where': 'Multiplexe Liberté',
            }


def parse_le_celtic() -> [dict]:
    soup = get_page('https://www.cgrcinemas.fr/brest/films-a-l-affiche/')
    today_number = now_in_year_month_day()[2]  # day number
    for elm in soup.find_all('a', **{'class': 'vignette url'}):
        subsoup = get_page(elm['href'])
        title = next(elm.text for elm in subsoup.find_all('h1'))
        # find numjour, the id (jour1, jour2,… jour9) that corresponds to today
        for celjour in subsoup.find_all('div', **{'class': 'fcel'}):
            if 'celtags' in celjour.attrs:
                continue  # this is not what we are looking for
            # print(celjour.text)
            noms = tuple(celjour.find_all('a', **{'class': 'hr_jour'}))
            # print(noms)
            # print()
            if not noms: continue
            assert len(noms) == 1, noms
            if int(tuple(noms[0].children)[1].strip()) == today_number:
                numjour = celjour.attrs['class'][1]
                break
        else:
            # print(f"Today ({today_number}) wasn't found in CGR data for movie {title}.")
            continue  # that's ok: the movie is probably not yet out
        # print('NUMJOUR:', numjour)
        target = tuple(subsoup.find_all('div', **{'class': f'tab_seances {numjour}'})) or tuple(subsoup.find_all('div', **{'class': f'tab_seances {numjour} active'}))
        assert len(target) == 1, len(target)
        target = target[0]
        # print(target)
        hours = []
        for kindline in target.find_all('div', **{'class': 'frow'}):
            if 'VO' in kindline.attrs['id']:
                kind = 'VO'
            elif 'VF' in kindline.attrs['id']:
                kind = 'VF'
            else:
                kind = 'VF'
                print(f"kindline {kindline.attrs['id']} not handled. {kind} will be used.")
            hours.extend(tuple((e.text.strip(), kind) for e in kindline.find_all('span', **{'class': 'hor'})))

        yield {
            'title': title,
            'synopsis': next(iter(subsoup.find_all('p', **{'class': 'ff_synopsis'}))).text.strip(),
            'today': hours,
            'where': 'Le Celtic',
        }



def repr_hour_and_kind(it:iter) -> [str]:
    return tuple(f"{h} ({k}) à {w}" for h, k, w in it)

def slugified(title: str) -> str:
    "Tries hard to get a unique representation of given movie title"
    title = title.lower().replace(' :', '').replace(' -', '').replace('  ', ' ').replace(' ', '-')
    unwanted = '():\'"'
    OK = {v: k for k, vs in {
        'a': 'àäâ',
        'e': 'èëêé',
        'i': 'ìïî',
        'o': 'òöô',
        'u': 'ùüû',
    }.items() for v in vs}
    return ''.join(OK.get(c, c) for c in title if c not in unwanted)


CACHE = {}
def parse_all(use_cache: bool = True):
    global CACHE
    CACHE = load_cache() if use_cache else {}
    if use_cache: save_cache()
    if use_cache: print(f"{len(CACHE)} pages cached")
    movies = {}  # name -> horaires
    def gen_all():
        yield from parse_les_studios()
        yield from parse_paté_gaumont()
        yield from parse_le_celtic()
    for movie in gen_all():
        slug = slugified(movie['title'])
        if not movie['today']:
            continue  # ignore that one, there is no séances today
        obj = movies.setdefault(slug, {})
        obj.setdefault('today', []).extend((hour, kind, movie['where']) for hour, kind in movie['today'])
        obj.setdefault('hours', []).extend((hour, kind, movie['where']) for hour, kind in movie['today'] if is_in_the_future(hour))
        if 'slug' in movie and len(movie['slug']) > len(obj.get('slug', '')):
            obj['slug'] = movie['slug']
        if 'where' in movie and len(movie['where']) > len(obj.get('where', '')):
            obj['where'] = movie['where']
        if 'title' in movie and len(movie['title']) > len(obj.get('title', '')):
            obj['title'] = movie['title']
        if 'synopsis' in movie and len(movie['synopsis']) > len(obj.get('synopsis', '')):
            obj['synopsis'] = movie['synopsis']
    for movie in movies.values():
        movie['desc_hours'] = repr_hour_and_kind(movie['hours'])
        movie['desc_today'] = repr_hour_and_kind(movie['today'])

    save_cache()
    yield from movies.values()
