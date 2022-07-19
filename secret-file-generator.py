import os
import shutil
from random import sample


correct_path = ['Dublin', 'Scopje', 'Valletta', 'Ljubljiana', 'London']
correct_code = '8324'

cities_per_level = 10

cities = [
    'Reykjavik',
    'Helsinki',
    'Oslo',
    'Stockholm',
    'Tallinn',
    'Riga',
    'Moscow',
    'Copenhagen',
    'Vilnius',
    'Minsk',
    'Dublin',
    'Amsterdam',
    'Berlin',
    'London',
    'Warsaw',
    'Brussels',
    'Kyiv',
    'Prague',
    'Luxembourg',
    'Paris',
    'Bratislava',
    'Vienna',
    'Budapest',
    'Vaduz',
    'Chisnau',
    'Bern',
    'Ljubljiana',
    'Zagreb',
    'Belgrade',
    'Bucharest',
    'Monaco',
    'San Marino',
    'Sarajevo',
    'Andorra la Vella',
    'Sofia',
    'Pristina',
    'Podgorica',
    'Vatican City',
    'Rome',
    'Scopje',
    'Tirana',
    'Madrid',
    'Lisbon',
    'Athens',
    'Valletta',
    'Nicosia'
]

assert cities_per_level <= len(cities)

levels = len(correct_path)

folder_name = 'secret_folder'

if os.path.isdir(folder_name):
    shutil.rmtree(folder_name)
os.mkdir(folder_name)
os.chdir(folder_name)

def create_layer(level=0):
    if level == levels:
        with open('secret.txt', 'w') as f:
            f.write(''.join(sample('0123456789', 4)))
            f.close()
    else:
        correct_city = correct_path[level]
        os.mkdir(correct_city)
        os.chdir(correct_city)
        create_layer(level + 1)
        os.chdir('..')
        for city in sample([c for c in cities if c != correct_city], cities_per_level):
            os.mkdir(city)
            os.chdir(city)
            create_layer(level + 1)
            os.chdir('..')


create_layer()
for city in correct_path:
    os.chdir(city)
with open('secret.txt', 'w') as f:
    f.write(correct_code)
    f.close()
