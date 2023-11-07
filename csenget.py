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

    try:
        with open('days.json', 'r', encoding='utf-8') as f:
            days = json.loads(f.read())
    except FileNotFoundError:
        print(f'No file days.json!')
        exit(-1)

    print(f"\nUsing {file_name} as input.\n")

    for k, v in times.items():
        print(k, v)
    while True:
        now = datetime.datetime.now()

        day = now.strftime("%A")
        hour = now.hour
        minute = now.minute
        sec = now.second

        current_time = f"{hour:02}:{minute:02}:{sec:02}"
        print(f"\r{day}: {days[day]} - {current_time}", end=f"\r", flush=True)
        if current_time in times and days[day] == 1:
            pygame.mixer.music.load(times[current_time])
            pygame.mixer.music.play()
            while pygame.mixer.music.get_busy():
                pass
        time.sleep(1)


if __name__ == "__main__":
    file_name = "normal.json"
    if len(sys.argv) > 1:
        file_name = sys.argv[1]
    main(file_name)
