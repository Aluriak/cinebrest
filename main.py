
from parse_sites import parse_all, now_in_hour_and_minutes

movie_ignored = set()
for movie in parse_all():
    if movie['hours']:
        print()
        print('——————————————————————————————————————————————')
        print(movie['title'])
        for desc in movie['hours']:
            print('\t' + desc)
        nb_ignored = len(movie['today']) - len(movie['hours'])
        if nb_ignored:
            print(f"({nb_ignored} séances ont été ignorées car démarrant avant {now_in_hour_and_minutes(str)})")
    else:
        movie_ignored.add(movie['title'])
if movie_ignored:
    print(f"{len(movie_ignored)} films ont été ignorés car il n'y a plus de séances aujourd'hui après {now_in_hour_and_minutes(str)}.")
