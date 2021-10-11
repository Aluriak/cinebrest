"""Parse websites, write html"""

import sys
import markdown
from parse_sites import parse_all, now_in_hour_and_minutes, now_in_year_month_day

OUTFILE = 'index.html'

def run() -> [str]:
    movie_ignored = set()
    for movie in parse_all(use_cache=False):
        if movie['hours']:
            yield f"\n\n## {movie['title']}\n"
            for desc in movie['desc_hours']:
                yield '- ' + desc
            nb_ignored = len(movie['today']) - len(movie['hours'])
            if nb_ignored:
                yield f"\n<small>({nb_ignored} séances ont été ignorées car démarrant avant {now_in_hour_and_minutes(str)})</small>"
        else:
            movie_ignored.add(movie['title'])
    if movie_ignored:
        yield f"\n<br/><br/><small>{len(movie_ignored)} films ont été ignorés car il n'y a plus de séances aujourd'hui après {now_in_hour_and_minutes(str)}.</small>"
    yield f"\n<br><br><small>Last update the {now_in_year_month_day(str)} at {now_in_hour_and_minutes(str)}</small>"


if __name__ == "__main__":
    html = markdown.markdown('\n'.join(run()))
    outfile = sys.argv[1] if len(sys.argv) > 1 else OUTFILE
    with open(outfile, 'w') as fd:
        fd.write(html)
