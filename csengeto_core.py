"""Közös állapot- és konfigurációkezelés a csengő programhoz.

- a beállításokat a settings.json fájlban tárolja
- a normál / rövidített órarendet a normal.json / rovid.json fájlokban
- a napokat a days.json fájlban
- gondoskodik arról, hogy egyszerre csak egy csengő-folyamat fusson
"""

from __future__ import annotations

import datetime
import json
import os
import re
import subprocess
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
SETTINGS_FILE = BASE_DIR / "settings.json"
DAYS_FILE = BASE_DIR / "days.json"
SCHEDULES = {"normal": BASE_DIR / "normal.json",
             "rovid": BASE_DIR / "rovid.json"}
SCHEDULE_LABELS = {"normal": "Normál órák", "rovid": "Rövidített órák"}
MODES = ("normal", "rovid")

DAYS = ("Monday", "Tuesday", "Wednesday",
        "Thursday", "Friday", "Saturday", "Sunday")
DAY_LABELS = {
    "Monday": "Hétfő",
    "Tuesday": "Kedd",
    "Wednesday": "Szerda",
    "Thursday": "Csütörtök",
    "Friday": "Péntek",
    "Saturday": "Szombat",
    "Sunday": "Vasárnap",
}

LOG_FILE = BASE_DIR / "csengeto.log"
ENGINE = BASE_DIR / "csenget.py"

DEFAULT_SETTINGS = {"mode": "normal", "sound": "joreggelt.mp3"}

TIME_RE = re.compile(r"^([01]?\d|2[0-3]):([0-5]\d)(?::([0-5]\d))?$")


# --------------------------------------------------------------------------- fájlok


def load_json(path: Path, default):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return default() if callable(default) else default


def save_json(path: Path, data) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")
    os.replace(tmp, path)


def load_settings() -> dict:
    data = load_json(SETTINGS_FILE, {})
    settings = dict(DEFAULT_SETTINGS)
    if isinstance(data, dict):
        settings.update({k: v for k, v in data.items()
                        if k in DEFAULT_SETTINGS})
    if settings["mode"] not in MODES:
        settings["mode"] = "normal"
    if not isinstance(settings["sound"], str) or not settings["sound"].strip():
        settings["sound"] = DEFAULT_SETTINGS["sound"]
    return settings


def save_settings(settings: dict) -> None:
    save_json(SETTINGS_FILE, settings)


def schedule_path(mode: str) -> Path:
    return SCHEDULES[mode if mode in MODES else "normal"]


def load_schedule(mode: str) -> dict[str, str]:
    data = load_json(schedule_path(mode), {})
    if not isinstance(data, dict):
        return {}
    times: dict[str, str] = {}
    for key, value in data.items():
        normalized = normalize_time(str(key))
        if normalized:
            times[normalized] = str(value)
    return times


def save_schedule(mode: str, times: dict[str, str]) -> None:
    save_json(schedule_path(mode), dict(sorted(times.items())))


def load_days() -> dict[str, int]:
    data = load_json(DAYS_FILE, {})
    days = {}
    for day in DAYS:
        value = data.get(day, 0) if isinstance(data, dict) else 0
        days[day] = 1 if value in (1, True, "1") else 0
    return days


def save_days(days: dict[str, int]) -> None:
    save_json(DAYS_FILE, {day: int(days.get(day, 0)) for day in DAYS})


# --------------------------------------------------------------------------- idő


def normalize_time(text: str) -> str | None:
    """'7:5' / '07:05' / '07:05:30' -> 'HH:MM:SS' (vagy None, ha érvénytelen)."""
    m = TIME_RE.match(text.strip())
    if not m:
        return None
    hour, minute, second = m.groups()
    return f"{int(hour):02d}:{int(minute):02d}:{int(second or 0):02d}"


def short_time(time_text: str) -> str:
    return time_text[:5]


def sounds_available() -> list[str]:
    return sorted(p.name for p in BASE_DIR.iterdir() if p.is_file() and p.suffix.lower() in (".mp3", ".wav", ".ogg"))


def sound_exists(name: str) -> bool:
    return (BASE_DIR / name).is_file()


def is_playlist(value: str) -> bool:
    return value.strip().upper() == "PLAYLIST"


# --------------------------------------------------------------------------- folyamat

PID_FILE = BASE_DIR / ".csengeto.pid"
PORTS_FILE = BASE_DIR / ".csengeto.port"


def _pid_alive(pid: int) -> bool:
    if pid <= 0:
        return False
    if os.name == "nt":
        try:
            out = subprocess.run(
                ["tasklist", "/FI", f"PID eq {pid}", "/NH"],
                capture_output=True, text=True, timeout=5,
            ).stdout
        except Exception:
            return False
        return str(pid) in out
    try:
        os.kill(pid, 0)
    except OSError:
        return False
    return True


def engine_pid() -> int | None:
    try:
        pid = int(PID_FILE.read_text(encoding="utf-8").strip())
    except (FileNotFoundError, ValueError):
        return None
    if _pid_alive(pid):
        return pid
    try:
        PID_FILE.unlink()
    except OSError:
        pass
    return None


def is_running() -> bool:
    return engine_pid() is not None


def start_engine() -> tuple[bool, str]:
    pid = engine_pid()
    if pid is not None:
        return False, f"A csengő már fut (PID {pid})."
    log = open(LOG_FILE, "a", encoding="utf-8", errors="replace")
    creationflags = 0
    if os.name == "nt":
        creationflags = getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0) | getattr(
            subprocess, "CREATE_NO_WINDOW", 0
        )
    proc = subprocess.Popen(
        [sys.executable, str(ENGINE)],
        cwd=str(BASE_DIR),
        stdin=subprocess.DEVNULL,
        stdout=log,
        stderr=log,
        creationflags=creationflags,
        env={**os.environ, "PYTHONIOENCODING": "utf-8"},
    )
    log.close()
    PID_FILE.write_text(str(proc.pid), encoding="utf-8")
    return True, f"Csengő elindítva (PID {proc.pid}), {SCHEDULE_LABELS[load_settings()['mode']]}."


def _engine_pid_listening_on(port: int) -> int | None:
    """Windows: melyik PID figyel az adott TCP porton."""
    if os.name != "nt":
        return None
    try:
        out = subprocess.run(["netstat", "-ano", "-p", "TCP"],
                             capture_output=True, text=True, timeout=10).stdout
    except Exception:
        return None
    for line in out.splitlines():
        parts = line.split()
        if len(parts) < 5 or parts[3] != "LISTENING":
            continue
        if parts[1].endswith(f":{port}"):
            try:
                return int(parts[4])
            except ValueError:
                return None
    return None


def _port_answered(port: int) -> bool:
    import socket

    try:
        with socket.create_connection(("127.0.0.1", port), timeout=1):
            return True
    except OSError:
        return False


def stop_engine() -> tuple[bool, str]:
    pid = engine_pid()
    port = None
    try:
        port = int(PORTS_FILE.read_text(encoding="utf-8").strip())
    except (FileNotFoundError, ValueError):
        pass

    if pid is None:
        # PID fájl eltűnt / elavult: próbáljuk a port alapján megkeresni
        if port and _port_answered(port):
            pid = _engine_pid_listening_on(port)
        if pid is None:
            return False, "A csengő nem fut."

    if os.name == "nt":
        subprocess.run(["taskkill", "/PID", str(pid), "/F"],
                       capture_output=True, text=True)
    else:
        try:
            os.kill(pid, 15)
        except OSError:
            pass
    try:
        PID_FILE.unlink()
    except OSError:
        pass
    if port:
        try:
            PORTS_FILE.unlink()
        except OSError:
            pass
    return True, f"Csengő leállítva (PID {pid})."


def now_text() -> str:
    now = datetime.datetime.now()
    return now.strftime("%Y. %m. %d.  %H:%M:%S")


# ------------------------------------------------------------------- próbacsengés

def _send_request(payload: dict) -> tuple[bool, str]:
    """Kérés küldése a futó csengőnek (a hangkártyát az birtokolja)."""
    import socket

    try:
        port = int(PORTS_FILE.read_text(encoding="utf-8").strip())
    except (FileNotFoundError, ValueError):
        return False, "A csengő nem fut – indítsd el a ▶ Indítás gombbal, vagy csengess a TUI-ból."
    try:
        with socket.create_connection(("127.0.0.1", port), timeout=2) as sock:
            sock.sendall(json.dumps(payload).encode("utf-8") + b"\n")
            sock.settimeout(5)
            reply = b""
            while not reply.endswith(b"\n"):
                chunk = sock.recv(4096)
                if not chunk:
                    break
                reply += chunk
            if reply:
                answer = json.loads(reply.decode("utf-8"))
                return bool(answer.get("ok")), str(answer.get("message", ""))
    except OSError as exc:
        return False, f"Nem sikerült kapcsolódni a csengőhöz: {exc}"
    return False, "A csengő nem válaszolt."


def test_play(sound: str) -> tuple[bool, str]:
    """Próbacsengés: ha fut a csengő, azt kérjük meg; különben itt játszuk le."""
    if not sound:
        return False, "Nincs megadva hangfájl."
    if is_playlist(sound):
        return False, "A PLAYLIST bejegyzéshez nincs egyetlen hang."
    if not sound_exists(sound):
        return False, f"A '{sound}' hangfájl nem található a mappában."

    if is_running():
        return _send_request({"action": "play", "sound": sound})

    try:
        import pygame
    except ImportError:
        return False, "A pygame nincs telepítve (pip install -r requirements.txt)."
    try:
        if not pygame.mixer.get_init():
            pygame.mixer.init()
        pygame.mixer.music.load(str(BASE_DIR / sound))
        pygame.mixer.music.play()
    except Exception as exc:  # pygame.error, OSError
        return False, f"Lejátszási hiba: {exc}"
    return True, f"Próbacsengés: {sound}"
