import datetime
import time
import pygame
import json
import sys

pygame.init()


def main(file_name):
    try:
        with open(file_name, 'r', encoding='utf-8') as f:
            times = json.loads(f.read())
    except FileNotFoundError:
        print(f'No data file {file_name}!')
        exit(-1)

    print(f"\nUsing {file_name} as input.\n")

    for k,v in times.items():
        print(k,v)
    while True:
        # A jelenlegi idő lekérdezése
        now = datetime.datetime.now()

        # Az óra és percek kiolvasása a dictionaryből
        hour = now.hour
        minute = now.minute
        sec = now.second

        # A hang lejátszása, ha a jelenlegi idő benne van a dictionaryben és hétköznap van

        current_time = f"{hour:02}:{minute:02}:{sec:02}"
        print(f"\r{current_time}", end=f"\r", flush=True)
        if current_time in times and now.weekday() < 6:
            # A hangfájl betöltése
            pygame.mixer.music.load(times[current_time])
            pygame.mixer.music.play()
            # A hang lejátszásának várása
            while pygame.mixer.music.get_busy():
                pass
        time.sleep(1)


if __name__ == "__main__":
    file_name = "normal.json"
    if len(sys.argv) > 1:
        file_name = sys.argv[1]
    main(file_name)
