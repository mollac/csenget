#!/usr/bin/env python3
"""Színes TUI kezelőfelület a csengő programhoz.

Indítás:  python tui.py

Funkciók:
  • a csengő folyamat ki-/bekapcsolása
  • óratípus váltás (Normál / Rövidített órák)
  • a KI/BE csengő időpontok és a lejátszandó hang szerkesztése
  • hivatalos/nem hivatalos napok beállítása
"""

from __future__ import annotations

import datetime

from rich.text import Text

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Grid, Horizontal, Vertical
from textual.message import Message
from textual.widgets import (
    Button,
    DataTable,
    Digits,
    Footer,
    Header,
    Input,
    Label,
    Select,
    Static,
)

import csengeto_core as core


def kind_of(sound: str) -> tuple[str, str]:
    """(jelzés, szín) a hangfájl alapján."""
    if core.is_playlist(sound):
        return "PLAYLIST", "bright_magenta"
    if "be" in sound.lower():
        return "BE", "bright_green"
    if "ki" in sound.lower():
        return "KI", "bright_red"
    return "EGYÉB", "bright_yellow"


class ClockDigits(Digits):
    def on_mount(self) -> None:
        self.update("00:00:00")


class ServiceSwitch(Static):
    """Nagy, szines ki/be kapcsolo."""

    class Toggled(Message):
        def __init__(self, switch: "ServiceSwitch", value: bool) -> None:
            self.switch = switch
            self.value = value
            super().__init__()

        @property
        def control(self) -> "ServiceSwitch":
            return self.switch

    def __init__(self, value: bool = False, **kwargs) -> None:
        self._value = value
        super().__init__(**kwargs)
        self.can_focus = True

    @property
    def value(self) -> bool:
        return self._value

    def on_mount(self) -> None:
        self.set_class(self._value, "on")

    def on_click(self) -> None:
        self._value = not self._value
        self.set_class(self._value, "on")
        self.refresh()
        self.post_message(self.Toggled(self, self._value))

    def action_toggle(self) -> None:
        self.on_click()

    BINDINGS = [Binding("enter,space", "toggle", "Ki/Bekapcsolás", show=False)]

    def render(self) -> Text:
        return Text("  BE  ●" if self._value else "○  KI  ")

    def set_value(self, value: bool) -> None:
        if value != self._value:
            self._value = value
            self.set_class(value, "on")
            self.refresh()


class CsengetoApp(App):
    """Csengő vezérlőpult."""

    TITLE = "CSENGŐ VEZÉRLŐPULT"
    SUB_TITLE = "kezelőfelület"

    CSS = """
    Screen {
        background: #0f1724;
        color: #dbe6f3;
    }

    Header {
        background: #17314f;
        color: #cfe3f8;
        text-style: bold;
    }

    Footer {
        background: #17314f;
        color: #9fb6ce;
    }

    /* ------------------------------------------------ felső sáv */
    #topbar {
        width: 100%;
        height: 14;
    }

    #clock {
        width: 38;
        height: 100%;
        padding: 0;
        background: #0a1120;
        border: round #3fa9f5;
        align: center middle;
    }

    #clock-digits {
        width: 36;
        min-width: 36;
        height: 3;
        color: #58c4ff;
        text-style: bold;
        text-align: center;
    }

    #state-card {
        width: 38;
        height: 100%;
        padding: 0 1;
        background: #0a1120;
        border: round #3fa9f5;
    }

    #state-line {
        height: 3;
        margin-top: 1;
        content-align: left middle;
        text-style: bold;
    }

    #status-line {
        height: 1;
        color: #8aa4c0;
    }

    #next-line {
        height: 1;
        color: #ffd166;
        text-style: bold;
    }

    #week-line {
        height: 1;
        color: #8aa4c0;
    }

    #daynames-line {
        height: 1;
        color: #5c7590;
    }

    #clock-sub {
        height: 1;
        color: #6b8299;
        content-align: center middle;
    }

    #controls {
        width: 1fr;
        height: 100%;
        padding: 0 1 0 1;
        background: #0a1120;
        border: round #3fa9f5;
        layout: grid;
        grid-size: 1 3;
        grid-columns: 1fr;
        grid-rows: 3 3 7;
        grid-gutter: 0;
    }

    #hdr {
        display: none;
    }

    #mode-cell, #switch-cell {
        height: 3;
        min-height: 3;
        align-vertical: middle;
    }

    #mode-cell Label, #switch-cell Label {
        width: auto;
        min-width: 10;
        height: 3;
        padding: 0 1 0 0;
        content-align: left middle;
        color: #9ec5e8;
    }

    #mode-select {
        width: 1fr;
        height: 3;
    }

    #service-switch {
        width: 13;
        min-width: 13;
        height: 2;
        min-height: 2;
        max-height: 2;
        margin: 0 0 0 1;
        padding: 0 1;
        border: none;
        background: #b23a48;
        color: #ffffff;
        content-align: center middle;
        text-style: bold;
    }

    #service-switch.on {
        background: #22a55a;
        color: #04150b;
    }

    #service-switch:focus {
        background: #ff5c6e;
    }

    #service-switch.on:focus {
        background: #3ddc84;
    }

    #switch-caption {
        width: 1fr;
        min-width: 8;
        height: 3;
        padding: 0 0 0 1;
        content-align: left middle;
        text-style: bold;
    }

    #button-row {
        layout: grid;
        grid-size: 2 2;
        grid-columns: 1fr 1fr;
        grid-rows: 3 3;
        height: 7;
        min-height: 7;
        grid-gutter: 1 1;
        padding: 0 1 0 0;
    }

    #button-row Button {
        height: 3;
        min-height: 3;
        width: 100%;
        min-width: 0;
        margin: 0;
        padding: 0 1;
        text-align: center;
        content-align: center middle;
    }


    #btn-stop {
        background: #c8404d;
        color: #ffffff;
    }

    #btn-stop:hover {
        background: #e05563;
    }

    #btn-stop:disabled {
        background: #8f3541;
        color: #ffd9dd;
        opacity: 100%;
    }

    #btn-start:disabled {
        background: #1f3b36;
        color: #7f9d96;
        opacity: 100%;
    }

    /* ------------------------------------------------ alsó terület */
    #schedule-box, #sounds-box, #days-box {
        border: round #3fa9f5;
        background: #0a1120;
        padding: 0 1;
    }

    #schedule-box {
        width: 1fr;
        padding: 0 1 1 1;
    }

    #side {
        width: 50;
        min-width: 50;
    }

    #sounds-box {
        height: 1fr;
    }

    #days-box {
        height: 7;
        min-height: 7;
        padding: 0 1 0 1;
    }

    #days-box .box-title {
        height: 2;
    }

    .box-title {
        height: 2;
        padding: 1 0 0 0;
        text-style: bold;
        color: #9ec5e8;
        background: transparent;
    }

    #schedule, #sound-list {
        height: 1fr;
        background: #0a1120;
    }

    #time-row, #sound-row {
        height: 3;
        min-height: 3;
        align-vertical: middle;
    }

    #time-row Label {
        width: auto;
        min-width: 0;
        height: 3;
        padding: 0 1 0 0;
        content-align: left middle;
        color: #9ec5e8;
    }

    #time-input {
        width: 12;
        min-width: 12;
        margin-right: 1;
    }

    #sound-select {
        width: 1fr;
        min-width: 20;
        height: 3;
    }

    #sound-input {
        width: 1fr;
        border: none;
        background: #131e31;
    }

    #sound-input:focus {
        border: none;
        background: #1b2a42;
    }

    #sound-row Button {
        height: 3;
        min-height: 3;
        margin: 0 0 0 1;
        padding: 0 1;
        text-style: none;
        text-align: center;
        content-align: center middle;
        color: #ffffff;
    }

    #sound-row Button > .button--label {
        height: 3;
        content-align: center middle;
    }

    #sound-row #btn-set-sound {
        background: #2a9d8f;
    }

    #sound-row #btn-preview {
        background: #3fa9f5;
        color: #06111f;
    }

    #sound-row #btn-set-sound {
        width: 13;
        min-width: 13;
    }

    #sound-row #btn-preview {
        width: 15;
        min-width: 15;
    }

    #side {
        width: 54;
        min-width: 54;
    }

    #sound-row {
        height: 3;
        min-height: 3;
        max-height: 3;
        border-top: solid #1b2a42;
        padding-top: 0;
        align-vertical: middle;
    }

    #day-grid {
        height: 3;
        min-height: 3;
        layout: grid;
        grid-size: 7 1;
        grid-columns: 1fr 1fr 1fr 1fr 1fr 1fr 1fr;
        grid-rows: 3;
        grid-gutter: 0 1;
    }

    #day-grid Button {
        height: 3;
        min-height: 3;
        min-width: 0;
        margin: 0;
        padding: 0;
        text-style: none;
    }

    #button-row-hint {
        height: 3;
        min-height: 3;
        max-height: 3;
    }

    #button-row-hint {
        layout: grid;
        grid-size: 3 1;
        grid-columns: 1fr 1fr 1fr;
        grid-rows: 3;
        grid-gutter: 0 1;
        padding: 0;
    }

    #button-row-hint Button {
        height: 3;
        min-height: 3;
        width: 100%;
        min-width: 0;
        margin: 0;
        padding: 0;
        text-align: center;
        content-align: center middle;
    }

    /* ------------------------------------------------ színek */
    .day-on {
        background: #2a9d8f;
        color: #ffffff;
        border: none;
    }

    .day-off {
        background: #2b3550;
        color: #7f8ea3;
        border: none;
    }

    .ok {
        background: #2a9d8f;
        color: #ffffff;
        border: none;
    }

    .ok:hover {
        background: #34b5a5;
    }

    .primary {
        background: #3fa9f5;
        color: #06111f;
        text-style: bold;
        border: none;
    }

    .primary:hover {
        background: #6cc0fb;
    }

    .danger {
        background: #d64550;
        color: #ffffff;
        border: none;
    }

    .danger:hover {
        background: #e35d67;
    }

    Button {
        border: none;
        height: 3;
        min-height: 3;
        width: auto;
        min-width: 10;
        padding: 0 1;
        background: #22405f;
        color: #dbe6f3;
        text-style: none;
        text-align: center;
        content-align: center middle;
    }

    Button > .button--label {
        width: 1fr;
        height: 1;
        background: #22405f;
        color: #dbe6f3;
        text-style: none;
        text-align: center;
        content-align: center middle;
        padding: 0;
    }

    Button:hover {
        background: #2d5378;
    }

    Button:hover > .button--label {
        background: #2d5378;
    }

    Button:focus {
        background: #3fa9f5;
    }

    Button:focus > .button--label {
        background: #3fa9f5;
        color: #06111f;
    }

    /* ---------------------------------------------- gomb-színek */
    .ok, .ok > .button--label {
        background: #2a9d8f;
        color: #ffffff;
    }

    .ok:hover, .ok:hover > .button--label {
        background: #34b5a5;
    }

    .primary, .primary > .button--label {
        background: #3fa9f5;
        color: #06111f;
    }

    .primary:hover, .primary:hover > .button--label {
        background: #6cc0fb;
    }

    .danger, .danger > .button--label {
        background: #c8404d;
        color: #ffffff;
    }

    .danger:hover, .danger:hover > .button--label {
        background: #e05563;
    }

    .day-on, .day-on > .button--label {
        background: #2a9d8f;
        color: #ffffff;
    }

    .day-on:hover, .day-on:hover > .button--label {
        background: #34b5a5;
    }

    .day-off, .day-off > .button--label {
        background: #2b3550;
        color: #7f8ea3;
    }

    .day-off:hover, .day-off:hover > .button--label {
        background: #3a4664;
    }

    #btn-start:disabled, #btn-start:disabled > .button--label {
        background: #1f3b36;
        color: #7f9d96;
    }

    #btn-stop:disabled, #btn-stop:disabled > .button--label {
        background: #8f3541;
        color: #ffd9dd;
    }

    #btn-reload, #btn-reload > .button--label {
        background: #22405f;
        color: #dbe6f3;
    }

    #btn-reload:hover, #btn-reload:hover > .button--label {
        background: #2d5378;
    }

    #btn-test, #btn-test > .button--label {
        background: #22405f;
        color: #dbe6f3;
    }

    #btn-test:hover, #btn-test:hover > .button--label {
        background: #2d5378;
    }

    #btn-set-sound, #btn-set-sound > .button--label {
        background: #2a9d8f;
        color: #ffffff;
    }

    #btn-preview, #btn-preview > .button--label {
        background: #3fa9f5;
        color: #06111f;
    }

    #btn-add, #btn-add > .button--label {
        background: #2a9d8f;
        color: #ffffff;
    }

    #btn-edit, #btn-edit > .button--label {
        background: #3fa9f5;
        color: #06111f;
    }

    #btn-delete, #btn-delete > .button--label {
        background: #c8404d;
        color: #ffffff;
    }

    #status {
        height: 1;
        padding: 0 1;
        color: #8aa4c0;
    }

    #status.error {
        color: #ff7782;
        text-style: bold;
    }

    #status.ok {
        background: transparent;
        color: #6fdc8c;
    }

    Input {
        background: #131e31;
    }

    Select {
        background: #131e31;
        border: tall #3fa9f5;
        color: #dbe6f3;
    }

    #btn-reload, #btn-test {
        background: #22405f;
        color: #dbe6f3;
        border: none;
    }

    #btn-reload:hover, #btn-test:hover {
        background: #2d5378;
    }

    Select > SelectCurrent {
        border: none;
        background: #131e31;
        color: #dbe6f3;
    }

    Select > SelectCurrent:hover {
        background: #1b2a42;
    }

    Input:focus {
        border: tall #6cc0fb;
    }

    DataTable {
        scrollbar-color: #1e4a75;
        scrollbar-color-hover: #3fa9f5;
        scrollbar-color-active: #3fa9f5;
        scrollbar-background: #0a1120;
        scrollbar-size: 1 1;
    }

    DataTable > .datatable--header {
        background: #17314f;
        color: #9ec5e8;
        text-style: bold;
    }

    DataTable > .datatable--cursor {
        background: #1e4a75;
        color: #ffffff;
        text-style: bold;
    }

    DataTable > .datatable--hover {
        background: #16243a;
    }

    Input.duplicate {
        border: tall #ff7782;
        background: #2a1520;
    }

    Input.duplicate:focus {
        border: tall #ff7782;
    }

    #time-input {
        border: tall #2b3a55;
    }

    #time-input:focus {
        border: tall #6cc0fb;
    }

    #schedule, #sound-list {
        border: none;
        background: #0a1120;
        overflow-x: hidden;
        scrollbar-size-horizontal: 0;
        scrollbar-size-vertical: 1;
    }

    #schedule:focus, #sound-list:focus {
        border: none;
    }

    #schedule:focus {
        border: none;
    }

    """

    BINDINGS = [
        Binding("ctrl+s", "toggle_service", "Ki/Bekapcsolás", priority=True),
        Binding("ctrl+t", "toggle_mode", "Óratípus", priority=True),
        Binding("ctrl+r", "reload", "Újratöltés", priority=True),
        Binding("ctrl+p", "check_now", "Próba csengés",
                priority=True, show=False),
        Binding("f2", "focus_schedule", "Időpontok", show=False),
        Binding("escape", "focus_schedule", "Időpontok", show=False),
        Binding("ctrl+q", "quit", "Kilépés", priority=True),
    ]

    def __init__(self) -> None:
        super().__init__()
        self.settings = core.load_settings()
        self.times: dict[str, str] = core.load_schedule(self.settings["mode"])
        self.days: dict[str, int] = core.load_days()
        self._ready_app = False
        self._last_running: bool | None = None

    # ------------------------------------------------------------------ felület

    def compose(self) -> ComposeResult:
        yield Header(show_clock=False, id="hdr")

        with Horizontal(id="topbar"):
            with Vertical(id="clock"):
                yield ClockDigits("00:00:00", id="clock-digits")
                yield Static("", id="clock-sub")
            with Vertical(id="state-card"):
                yield Static("● FOLYAMAT", id="state-line")
                yield Static("betöltés...", id="status-line")
                yield Static("", id="next-line")
                yield Static("", id="week-line")
                yield Static("", id="daynames-line")
            with Vertical(id="controls"):
                with Horizontal(id="mode-cell"):
                    yield Label("Óratípus: ")
                    yield Select(
                        [(label, mode)
                         for mode, label in core.SCHEDULE_LABELS.items()],
                        value=self.settings["mode"],
                        allow_blank=False,
                        id="mode-select",
                    )
                with Horizontal(id="switch-cell"):
                    yield Label("Csengő:")
                    yield ServiceSwitch(value=False, id="service-switch")
                with Horizontal(id="button-row"):
                    yield Button("▶ Indítás", id="btn-start", classes="ok")
                    yield Button("■ Leállítás", id="btn-stop", classes="danger")
                    yield Button("↻ Újratöltés", id="btn-reload")
                    yield Button("◈ Próba csengés", id="btn-test")

        with Horizontal(id="main"):
            with Vertical(id="schedule-box"):
                yield Static("IDŐPONTOK", classes="box-title")
                yield DataTable(id="schedule", cursor_type="row", zebra_stripes=True)
                with Horizontal(id="time-row"):
                    yield Label("Időpont: ")
                    yield Input(placeholder="HH:MM", id="time-input")
                    yield Label(" Hang: ")
                    yield Select([], id="sound-select", prompt="hangfájl")
                with Horizontal(id="button-row-hint"):
                    yield Button("＋ Hozzáadás", id="btn-add", classes="ok")
                    yield Button("✎ Módosítás", id="btn-edit", classes="primary")
                    yield Button("✕ Törlés", id="btn-delete", classes="danger")

            with Vertical(id="side"):
                with Vertical(id="sounds-box"):
                    yield Static("HANGOK", classes="box-title")
                    yield DataTable(id="sound-list", cursor_type="row", zebra_stripes=True)
                    with Horizontal(id="sound-row"):
                        yield Input(placeholder="hang.mp3", id="sound-input")
                        yield Button("Alkalmaz", id="btn-set-sound")
                        yield Button("▶ Hallgasd", id="btn-preview")
                with Vertical(id="days-box"):
                    yield Static("NAPI BEKAPCSOLÁS", classes="box-title")
                    with Grid(id="day-grid"):
                        for day in core.DAYS:
                            yield Button(core.DAY_LABELS[day][:3].upper(), id=f"day-{day}", classes="day-on")

        yield Static("", id="status")
        yield Footer()

    def on_mount(self) -> None:
        self.digits = self.query_one("#clock-digits", ClockDigits)
        self.clock_sub = self.query_one("#clock-sub", Static)
        self.state_line = self.query_one("#state-line", Static)
        self.status_line = self.query_one("#status-line", Static)
        self.next_line = self.query_one("#next-line", Static)
        self.week_line = self.query_one("#week-line", Static)
        self.daynames_line = self.query_one("#daynames-line", Static)
        self.service_switch = self.query_one("#service-switch", ServiceSwitch)
        self.status = self.query_one("#status", Static)
        self.schedule = self.query_one("#schedule", DataTable)
        self.sound_list = self.query_one("#sound-list", DataTable)
        self.time_input = self.query_one("#time-input", Input)
        self.sound_input = self.query_one("#sound-input", Input)
        self.sound_select = self.query_one("#sound-select", Select)
        self.mode_select = self.query_one("#mode-select", Select)
        self.btn_start = self.query_one("#btn-start", Button)
        self.btn_stop = self.query_one("#btn-stop", Button)

        self.schedule.add_columns("Időpont", "Csengés", "Hang")
        self.sound_list.add_columns("Fájl", "Típus")

        self.refresh_schedule()
        self.refresh_sounds()
        self.refresh_days()
        self.refresh_state()
        self.update_clock()
        self._ready_app = True

        self.set_interval(0.2, self.update_clock)
        self.set_interval(2.0, self.refresh_state)
        self.set_interval(30.0, self.refresh_now_marker)

    # ------------------------------------------------------------- adat-frissítés

    def refresh_schedule(self) -> None:
        table = self.schedule
        saved_row = table.cursor_row
        table.clear()
        now = datetime.datetime.now().strftime("%H:%M:%S")
        next_time = next((t for t in sorted(self.times) if t > now), None)
        for time_text, sound in sorted(self.times.items()):
            kind, color = kind_of(sound)
            label = f"[{color}]{time_text[:5]}[/]"
            if time_text == next_time:
                label += "  [yellow]◀ következő[/]"
            table.add_row(label, f"[{color}]{kind}[/]", sound, key=time_text)
        if table.row_count and saved_row < table.row_count:
            table.move_cursor(row=max(0, saved_row))

    def refresh_now_marker(self) -> None:
        self.refresh_schedule()

    def refresh_sounds(self) -> None:
        table = self.sound_list
        table.clear()
        for name in core.sounds_available():
            kind, color = kind_of(name)
            table.add_row(name, f"[{color}]{kind}[/]", key=name)
        selected = self.selected_time()
        self._apply_switch(self.times.get(selected, "")
                           if selected else self.settings["sound"])

    def refresh_days(self) -> None:
        for day in core.DAYS:
            button = self.query_one(f"#day-{day}", Button)
            on = self.days.get(day) == 1
            button.set_class(on, "day-on")
            button.set_class(not on, "day-off")
            button.label = core.DAY_LABELS[day][:3].upper()

    def refresh_state(self) -> None:
        pid = core.engine_pid()
        running = pid is not None
        state = self.state_line
        status_line = self.status_line
        switch = self.service_switch

        if running:
            state.update(f"[bright_green]● CSENGŐ FUT[/] [dim]PID {pid}[/]")
            status_line.update(
                f"[cyan]{core.SCHEDULE_LABELS[self.settings['mode']]}")
        else:
            state.update("[bright_red]● CSENGŐ LEÁLLÍTVA[/]")
            status_line.update("[dim]indítsd el a ▶ gombbal[/]")

        now = datetime.datetime.now()
        today = now.strftime("%A")
        now_s = now.strftime("%H:%M:%S")
        if self.days.get(today) == 1 and self.times:
            upcoming = [t for t in sorted(self.times) if t > now_s]
            if upcoming:
                self.next_line.update(
                    f"[yellow]▼ {upcoming[0][:5]} – {self.times[upcoming[0]]}[/]")
            else:
                self.next_line.update("[dim]▼ mára nincs több csengés[/]")
        elif self.days.get(today) == 1:
            self.next_line.update("[dim]▼ nincs időpont[/]")
        else:
            self.next_line.update("[dim]▼ mai nap kikapcsolva[/]")
        week = Text()
        for index, day in enumerate(core.DAYS):
            if index:
                week.append("  ")
            week.append(
                core.DAY_LABELS[day][:2],
                style="bold #4ade80" if self.days.get(day) else "bold #f87171",
            )
        self.week_line.update(week)
        self.daynames_line.update("")

        if switch.value != running:
            switch.set_value(running)
        self._last_running = running
        self.btn_start.disabled = running
        self.btn_stop.disabled = not running

    def update_clock(self) -> None:
        now = datetime.datetime.now()
        self.digits.update(now.strftime("%H:%M:%S"))
        self.clock_sub.update(f"{core.DAY_LABELS[now.strftime('%A')]}")

    # ------------------------------------------------------------------ üzenetek

    def notify(self, text: str, error: bool = False) -> None:
        self.status.update(("✖ " if error else "✔ ") + text)
        self.status.set_class(error, "error")
        self.status.set_class(not error, "ok")

    def action_reload(self) -> None:
        self.settings = core.load_settings()
        self.times = core.load_schedule(self.settings["mode"])
        self.days = core.load_days()
        self.mode_select.value = self.settings["mode"]
        self.refresh_schedule()
        self.refresh_sounds()
        self.refresh_days()
        self.refresh_state()
        self.notify("Beállítások újratöltve.")

    def action_toggle_service(self) -> None:
        self.toggle_service()

    def action_toggle_mode(self) -> None:
        self.change_mode(
            "rovid" if self.settings["mode"] == "normal" else "normal")

    def action_focus_schedule(self) -> None:
        self.schedule.focus()

    def action_check_now(self) -> None:
        self.play_test()

    # ------------------------------------------------------------------ események

    def on_button_pressed(self, event: Button.Pressed) -> None:
        bid = event.button.id or ""
        if bid == "btn-start":
            self.start_service()
        elif bid == "btn-stop":
            self.stop_service()
        elif bid == "btn-reload":
            self.action_reload()
        elif bid == "btn-add":
            self.add_time()
        elif bid == "btn-edit":
            self.edit_selected()
        elif bid == "btn-delete":
            self.delete_selected()
        elif bid == "btn-set-sound":
            self.set_sound_for_selection(
                self.query_one("#sound-input", Input).value)
        elif bid == "btn-preview":
            self.play_test()
        elif bid == "btn-test":
            self.play_test()
        elif bid.startswith("day-"):
            self.toggle_day(bid[4:])

    def on_select_changed(self, event: Select.Changed) -> None:
        if event.select.id == "mode-select" and event.value in core.MODES:
            self.change_mode(str(event.value))

    def on_service_switch_toggled(self, event: ServiceSwitch.Toggled) -> None:
        if not self._ready_app:
            return
        if event.value:
            self.start_service()
        else:
            self.stop_service()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input.id == "time-input":
            self.add_time()
        elif event.input.id == "sound-input":
            self.set_sound_for_selection(event.value)

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        if event.data_table.id == "sound-list":
            self.set_sound_for_selection(
                str(event.row_key.value), advance=False)
        elif event.data_table.id == "schedule":
            self.edit_selected()

    def on_data_table_row_highlighted(self, event: DataTable.RowHighlighted) -> None:
        if event.data_table.id != "schedule":
            return
        value = event.row_key.value
        if value is None:
            return
        time_text = str(value)
        if time_text not in self.times:
            return
        # Ha a felhasználó épp gépel valamelyik mezőbe, ne írjuk felül a tartalmát.
        if self.time_input.has_focus or self.sound_input.has_focus:
            return
        self.time_input.value = time_text[:5]
        self.sound_input.value = self.times[time_text]

    # ------------------------------------------------------------------ műveletek

    def change_mode(self, mode: str) -> None:
        if mode == self.settings["mode"]:
            return
        self.settings["mode"] = mode
        core.save_settings(self.settings)
        self.times = core.load_schedule(mode)
        self.refresh_schedule()
        self.refresh_state()
        self.notify(f"Óratípus: {core.SCHEDULE_LABELS[mode]}")

    def toggle_service(self) -> None:
        self.service_switch.on_click()

    def start_service(self) -> None:
        if core.is_running():
            self.notify("A csengő már fut.", error=True)
            self.refresh_state()
            return
        ok, message = core.start_engine()
        self.notify(message, error=not ok)
        self.set_timer(1.0, self.refresh_state)

    def stop_service(self) -> None:
        pid = core.engine_pid()
        if pid is not None:
            # ugyanaz, mint a leállításnál; a folyamat PID-je alapján
            ok, message = core.stop_engine()
            self.notify(message, error=not ok)
        else:
            self.notify("A csengő nem fut.", error=True)
        self.set_timer(0.8, self.refresh_state)

    def flag_duplicate(self) -> None:
        """Piros keret a beviteli mezön, ha az időpont már létezik."""
        self.time_input.add_class("duplicate")
        self.set_timer(2.5, lambda: self.time_input.remove_class("duplicate"))

    def on_input_changed(self, event: Input.Changed) -> None:
        """Élő visszajelzés: a duplikált időpontot azonnal jelzi gépelés közben."""
        if event.input.id != "time-input":
            return
        text = event.value.strip()
        normalized = core.normalize_time(text) if text else None
        duplicate = normalized is not None and normalized in self.times
        self.time_input.set_class(duplicate, "duplicate")

    def add_time(self) -> None:
        normalized = core.normalize_time(self.time_input.value)
        value = self.sound_select.value
        sound = "" if value in (None, Select.BLANK) else str(value)
        if normalized is None:
            self.notify(
                f"Érvénytelen időpont: '{self.time_input.value.strip()}' – HH:MM formátum kell (pl. 07:50).", error=True)
            return
        if normalized in self.times:
            # ne lehessen kétszer felvenni ugyanazt az időpontot
            self.notify(
                f"A(z) {normalized[:5]} időpont már szerepel ({self.times[normalized]}) – "
                f"módosításhoz jelöld ki a listában vagy használd a ✎ Módosítás gombot.", error=True)
            self.flag_duplicate()
            return
        if not sound:
            self.notify("Válassz hangfájlt az új időponthoz!", error=True)
            return
        self.times[normalized] = sound
        core.save_schedule(self.settings["mode"], self.times)
        self.refresh_schedule()
        self.select_time(normalized)
        self.time_input.value = ""
        self.notify(f"{normalized[:5]} hozzáadva: {sound}")

    def select_time(self, time_text: str) -> None:
        """A megadott időpont sorára állítja a kurzort."""
        keys = sorted(self.times)
        if time_text in keys:
            self.schedule.move_cursor(row=keys.index(time_text))

    def selected_time(self) -> str | None:
        table = self.schedule
        if table.row_count == 0:
            return None
        try:
            row_key = table.coordinate_to_cell_key(
                table.cursor_coordinate).row_key
        except Exception:
            return None
        value = row_key.value
        return str(value) if value is not None else None

    def edit_selected(self) -> None:
        time_text = self.selected_time()
        if time_text is None:
            self.notify("Nincs kijelölt időpont.", error=True)
            return
        new_time = core.normalize_time(self.time_input.value)
        sound = self.sound_input.value.strip()
        if new_time is None:
            self.notify(
                f"Érvénytelen időpont: '{self.time_input.value.strip()}' – HH:MM formátum kell (pl. 07:50).", error=True)
            return
        if not sound:
            self.notify("Add meg a hangfájl nevét!", error=True)
            return
        if not core.sound_exists(sound) and not core.is_playlist(sound):
            self.notify(
                f"A '{sound}' hangfájl nem található a mappában.", error=True)
            return
        if new_time != time_text and new_time in self.times:
            # nem módosítható egy már létező időpontra
            self.notify(
                f"A(z) {new_time[:5]} időpont már szerepel ({self.times[new_time]}) – válassz másikat.", error=True)
            self.flag_duplicate()
            return
        del self.times[time_text]
        self.times[new_time] = sound
        core.save_schedule(self.settings["mode"], self.times)
        self.refresh_schedule()
        self.notify(f"{time_text[:5]} → {new_time[:5]} ({sound}) mentve.")

    def delete_selected(self) -> None:
        time_text = self.selected_time()
        if time_text is None:
            self.notify("Nincs kijelölt időpont.", error=True)
            return
        del self.times[time_text]
        core.save_schedule(self.settings["mode"], self.times)
        self.refresh_schedule()
        self.notify(f"{time_text[:5]} törölve.")

    def set_sound_for_selection(self, sound: str, advance: bool = True) -> None:
        sound = sound.strip()
        if not sound:
            self.notify("Adj meg / válassz hangfájlt.", error=True)
            return
        if not core.sound_exists(sound) and not core.is_playlist(sound):
            self.notify(
                f"A '{sound}' hangfájl nem található a mappában.", error=True)
            return
        time_text = self.selected_time()
        if time_text is None:
            self.notify("Előbb jelölj ki időpontot az órarendben.", error=True)
            return
        self.times[time_text] = sound
        core.save_schedule(self.settings["mode"], self.times)
        self.refresh_schedule()
        self.sound_input.value = sound
        self.notify(f"{time_text[:5]} hangja: {sound}")
        if advance and self.schedule.cursor_row + 1 < self.schedule.row_count:
            self.schedule.move_cursor(row=self.schedule.cursor_row + 1)

    def toggle_day(self, day: str) -> None:
        self.days[day] = 0 if self.days.get(day) == 1 else 1
        core.save_days(self.days)
        self.refresh_days()
        self.notify(
            f"{core.DAY_LABELS[day]}: {'bekapcsolva' if self.days[day] else 'kikapcsolva'}")

    def play_test(self) -> None:
        time_text = self.selected_time()
        sound = (self.times.get(time_text, "")
                 if time_text else "") or self.sound_input.value.strip()
        sound = sound or self.settings["sound"]
        ok, message = core.test_play(sound)
        self.notify(message, error=not ok)

    def _apply_switch(self, sound: str) -> None:
        options = [(name, name) for name in core.sounds_available()]
        self.sound_select.set_options(options)
        if options:
            names = [name for name, _ in options]
            self.sound_select.value = sound if sound in names else names[0]


def main() -> None:
    CsengetoApp().run()


if __name__ == "__main__":
    main()
