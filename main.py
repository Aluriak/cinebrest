
from parse_sites import parse_all

nb_movie_ignored = 0
for movie in parse_all():
    if movie['ok']:
        print()
        print('——————————————————————————————————————————————')
        print(movie['title'])
        print(movie['desc'])
        print('Horaires:', ', '.join(f"{h} ({k})" for h, k in movie['ok']), 'à', movie['where'])
    else:
        nb_movie_ignored += 1
