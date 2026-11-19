import datetime
import json
import os
import socket
import threading
import time

import pygame

import csengeto_core as core


class ControlServer:
    """Helyi TCP porton fogadja a TUI kéréseit (pl. próbacsengés)."""

    def __init__(self) -> None:
        self.sock: socket.socket | None = None
        self.port = 0

    def start(self) -> None:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.bind(("127.0.0.1", 0))
            sock.listen(5)
        except OSError as exc:
            print(f"Vezérlőport nem indítható: {exc}", flush=True)
            sock.close()
            return
        self.sock = sock
        self.port = sock.getsockname()[1]
        try:
            core.PORTS_FILE.write_text(str(self.port), encoding="utf-8")
        except OSError:
            pass
        threading.Thread(target=self._serve, daemon=True).start()

    def _serve(self) -> None:
        assert self.sock is not None
        while True:
            try:
                conn, _ = self.sock.accept()
            except OSError:
                return
            with conn:
                try:
                    conn.settimeout(3)
                    data = b""
                    while not data.endswith(b"\n"):
                        chunk = conn.recv(4096)
                        if not chunk:
                            break
                        data += chunk
                    request = json.loads(data.decode("utf-8") or "{}")
                    ok, message = self._handle(request)
                except Exception as exc:
                    ok, message = False, f"Hibás kérés: {exc}"
                try:
                    conn.sendall(json.dumps(
                        {"ok": ok, "message": message}).encode("utf-8") + b"\n")
                except OSError:
                    pass

    def _handle(self, request: dict) -> tuple[bool, str]:
        if request.get("action") == "play":
            sound = str(request.get("sound", ""))
            if not core.sound_exists(sound):
                return False, f"A '{sound}' hangfájl nem található."
            play(sound)
            return True, f"Próbacsengés: {sound}"
        return False, "Ismeretlen kérés."


def stop_audio() -> None:
    try:
        pygame.mixer.music.stop()
    except pygame.error:
        pass


def init_audio() -> bool:
    global _pygame_ready
    try:
        pygame.mixer.init()
        _pygame_ready = True
    except pygame.error as exc:  # nincs hangkártya / foglalt eszköz
        print(f"Hang inicializálás sikertelen: {exc}", flush=True)
        _pygame_ready = False
    return _pygame_ready


_pygame_ready = False


def play(sound: str) -> None:
    """Hang lejátszása háttérszálon, hogy az óra tovább ketyeghessen."""
    if core.is_playlist(sound) or not _pygame_ready:
        return
    path = core.BASE_DIR / sound
    if not path.is_file():
        print(f"Hangfájl nem található: {path}", flush=True)
        return

    def worker():
        try:
            pygame.mixer.music.load(str(path))
            pygame.mixer.music.play()
        except pygame.error as exc:
            print(f"Lejátszási hiba: {exc}", flush=True)

    threading.Thread(target=worker, daemon=True).start()


def run() -> None:
    core.PID_FILE.write_text(str(os.getpid()), encoding="utf-8")
    if core.PORTS_FILE.exists():
        try:
            core.PORTS_FILE.unlink()
        except OSError:
            pass
    init_audio()

    control = ControlServer()
    control.start()

    settings = core.load_settings()
    times = core.load_schedule(settings["mode"])
    days = core.load_days()
    print(
        f"Csengő elindult: {core.SCHEDULE_LABELS[settings['mode']]}, hang: {settings['sound']}",
        flush=True,
    )

    files_stamp = None
    last_second = None

    try:
        while True:
            try:
                # Ha a TUI módosított egy fájlt, töltse újra a beállításokat / órarendet.
                stamp = []
                for path in (core.SETTINGS_FILE, core.schedule_path(settings["mode"]), core.DAYS_FILE):
                    try:
                        stamp.append(path.stat().st_mtime_ns)
                    except OSError:
                        stamp.append(0)
                stamp_tuple = tuple(stamp)
                if stamp_tuple != files_stamp:
                    if files_stamp is not None:
                        print("Beállítások újratöltve.", flush=True)
                    files_stamp = stamp_tuple
                    old_mode = settings["mode"]
                    settings = core.load_settings()
                    if settings["mode"] != old_mode:
                        print(
                            f"Óratípus váltás: {core.SCHEDULE_LABELS[settings['mode']]}", flush=True)
                    times = core.load_schedule(settings["mode"])
                    days = core.load_days()

                now = datetime.datetime.now()
                current_time = now.strftime("%H:%M:%S")

                # Csak egyszer csörögjön egy időpontnál.
                if current_time != last_second:
                    last_second = current_time
                    if current_time in times and days.get(now.strftime("%A")) == 1:
                        sound = times[current_time]
                        print(
                            f"[{current_time}] {now.strftime('%A')}: {sound}", flush=True)
                        play(sound)

                time.sleep(0.2)
            except Exception as exc:  # a csengő ne álljon le egy hibától
                print(f"Hiba: {exc}", flush=True)
                time.sleep(1)
    except KeyboardInterrupt:
        print("Csengő leállítva.", flush=True)
    finally:
        cleanup()


def cleanup() -> None:
    stop_audio()
    try:
        if core.PID_FILE.read_text(encoding="utf-8").strip() == str(os.getpid()):
            core.PID_FILE.unlink()
    except OSError:
        pass
    try:
        core.PORTS_FILE.unlink()
    except OSError:
        pass


if __name__ == "__main__":
    run()
