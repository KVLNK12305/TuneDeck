"""
JBLPc — Beautiful Terminal UI for JBL Tune 770NC.

A gorgeous Textual-based TUI with:
- Real-time headset status dashboard
- ANC/Ambient/TalkThru controls
- 10-band graphical equalizer
- Battery monitoring
- Activity log
- Keyboard shortcuts

Color scheme: JBL's signature orange (#FF6600) on dark backgrounds.
"""

from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal, Vertical, ScrollableContainer
from textual.widgets import (
    Header,
    Footer,
    Static,
    Button,
    Label,
    ProgressBar,
    Log,
    Rule,
    Switch,
)
from textual.binding import Binding
from textual.reactive import reactive
from textual.timer import Timer
from textual import events
from rich.text import Text
from rich.panel import Panel
from rich.table import Table
from rich.console import Group
from rich.align import Align

from typing import Optional
from textual.css.query import NoMatches
from ..controller import HeadsetController, HeadsetState
from ..protocol import NoiseMode, EQPreset, EQ_PRESET_NAMES, MODE_NAMES
from ..health import BatteryHealthTracker


# ─── Custom Widgets ──────────────────────────────────────────────────────────

class BrandBanner(Static):
    """JBL branding banner with device info."""

    def compose(self) -> ComposeResult:
        yield Static(id="banner-content")

    def update_state(self, state: HeadsetState, simulating: bool = False):
        banner = self.query_one("#banner-content", Static)

        status_color = "green" if state.connected else "red"
        status_text = "● CONNECTED" if state.connected else "● DISCONNECTED"
        sim_badge = " [bold yellow]🧪 SIMULATOR[/]" if simulating else ""

        model_display = f"🎧 {state.device_name}"
        art = Text.from_markup(
            f"[bold #FF6600]╔══════════════════════════════════════════════════╗[/]\n"
            f"[bold #FF6600]║[/]  [bold white]{model_display:<30}[/] "
            f"[{status_color}]{status_text}[/]{sim_badge} [bold #FF6600]║[/]\n"
            f"[bold #FF6600]║[/]  [dim]{(state.bt_address or 'No address set'):<46}[/] [bold #FF6600]║[/]\n"
            f"[bold #FF6600]╚══════════════════════════════════════════════════╝[/]"
        )
        banner.update(art)


class BatteryWidget(Static):
    """Battery level display with visual bar (supports single & TWS trio)."""

    def compose(self) -> ComposeResult:
        yield Static(id="battery-display")

    def update_battery(self, level: int, state: Optional[HeadsetState] = None):
        display = self.query_one("#battery-display", Static)

        if state and state.shows_tws_trio:
            l = state.battery_left
            r = state.battery_right
            c = state.battery_case

            def fmt_mini(val):
                if val < 0:
                    return "[dim]??%[/]"
                color = "#00FF88" if val > 60 else ("#FFaa00" if val > 25 else "#FF3333")
                f = int(val / 20)
                e = 5 - f
                return f"[{color}]{'█'*f}[/][dim]{'░'*e}[/] [{color}]{val}%[/]"

            display.update(Text.from_markup(
                f"[bold #FF6600]🔋 TWS BATTERY[/]\n"
                f"  [bold]L:[/] {fmt_mini(l)}  [bold]R:[/] {fmt_mini(r)}  [bold]Case:[/] {fmt_mini(c)}"
            ))
            return

        if level < 0:
            display.update(Text.from_markup(
                "[bold #FF6600]🔋 BATTERY[/]\n"
                "[dim]  ░░░░░░░░░░ ???[/]"
            ))
            return

        # Color based on level
        if level > 60:
            color = "#00FF88"
        elif level > 25:
            color = "#FFaa00"
        else:
            color = "#FF3333"

        filled = int(level / 10)
        empty = 10 - filled
        bar = f"[{color}]{'█' * filled}[/][dim]{'░' * empty}[/]"

        display.update(Text.from_markup(
            f"[bold #FF6600]🔋 BATTERY[/]\n"
            f"  {bar} [{color}]{level}%[/]"
        ))


class NoiseControlWidget(Static):
    """Noise control mode selector with strict capability gating per model."""

    current_mode: reactive[NoiseMode] = reactive(NoiseMode.OFF)

    def __init__(self, controller: HeadsetController, **kwargs):
        super().__init__(**kwargs)
        self.controller = controller

    def compose(self) -> ComposeResult:
        yield Static(id="noise-header")
        with Horizontal(id="noise-buttons"):
            yield Button("OFF", id="noise-off", variant="default")
            yield Button("ANC", id="noise-anc", variant="default")
            yield Button("AMBIENT", id="noise-ambient", variant="default")
            yield Button("TALK", id="noise-talk", variant="default")
        yield Static("[dim italic]  Active noise cancellation is not supported on this model.[/]", id="noise-unsupported")

    def on_mount(self):
        self.update_capabilities(self.controller.state.profile)

    def update_capabilities(self, profile):
        """Update visible noise mode buttons based on hardware capabilities."""
        try:
            btn_box = self.query_one("#noise-buttons", Horizontal)
            unsupported = self.query_one("#noise-unsupported", Static)
            btn_off = self.query_one("#noise-off", Button)
            btn_anc = self.query_one("#noise-anc", Button)
            btn_ambient = self.query_one("#noise-ambient", Button)
            btn_talk = self.query_one("#noise-talk", Button)
        except NoMatches:
            return

        if not profile.has_anc:
            btn_box.display = False
            unsupported.display = True
        else:
            btn_box.display = True
            unsupported.display = False
            btn_off.display = True
            btn_anc.display = True
            btn_ambient.display = profile.has_ambient_aware
            btn_talk.display = profile.has_talkthru

        self._update_header()
        self._highlight_active(self.current_mode)

    def _update_header(self):
        try:
            header = self.query_one("#noise-header", Static)
        except NoMatches:
            return
        if not self.controller.state.profile.has_anc:
            header.update(Text.from_markup(
                "[bold #FF6600]🔇 NOISE CONTROL[/]  [dim]» Not supported[/]"
            ))
            return
        mode_name = MODE_NAMES.get(self.current_mode, "Unknown")
        header.update(Text.from_markup(
            f"[bold #FF6600]🔇 NOISE CONTROL[/]  [bold white]» {mode_name}[/]"
        ))

    def watch_current_mode(self, mode: NoiseMode):
        self._update_header()
        self._highlight_active(mode)

    def _highlight_active(self, mode: NoiseMode):
        mode_map = {
            NoiseMode.OFF: "noise-off",
            NoiseMode.ANC: "noise-anc",
            NoiseMode.AMBIENT_AWARE: "noise-ambient",
            NoiseMode.TALKTHRU: "noise-talk",
        }
        for m, btn_id in mode_map.items():
            try:
                btn = self.query_one(f"#{btn_id}", Button)
                if m == mode:
                    btn.variant = "warning"
                else:
                    btn.variant = "default"
            except NoMatches:
                pass

    def on_button_pressed(self, event: Button.Pressed) -> None:
        p = self.controller.state.profile
        mode_map = {
            "noise-off": NoiseMode.OFF,
            "noise-anc": NoiseMode.ANC,
            "noise-ambient": NoiseMode.AMBIENT_AWARE,
            "noise-talk": NoiseMode.TALKTHRU,
        }
        mode = mode_map.get(event.button.id)
        if mode is None:
            return

        # Double check model compatibility
        if mode == NoiseMode.ANC and not p.has_anc:
            return
        if mode == NoiseMode.AMBIENT_AWARE and not p.has_ambient_aware:
            return
        if mode == NoiseMode.TALKTHRU and not p.has_talkthru:
            return

        self.controller.set_noise_mode(mode)
        self.current_mode = mode


class EQBandSlider(Static):
    """A single EQ band displayed as a vertical bar in the terminal."""

    value: reactive[int] = reactive(0)
    is_selected: reactive[bool] = reactive(False)

    def __init__(self, band_index: int, freq_label: str, controller: HeadsetController, **kwargs):
        super().__init__(**kwargs)
        self.band_index = band_index
        self.freq_label = freq_label
        self.controller = controller

    def compose(self) -> ComposeResult:
        yield Static(id=f"eq-bar-{self.band_index}")

    def on_mount(self):
        self._render_bar()

    def watch_value(self, val: int):
        self._render_bar()

    def watch_is_selected(self, val: bool):
        self._render_bar()

    def _render_bar(self):
        try:
            bar = self.query_one(f"#eq-bar-{self.band_index}", Static)
        except NoMatches:
            return

        # Build vertical bar visualization (13 steps: -6 to +6, mapped from -12 to +12)
        display_val = max(-6, min(6, self.value // 2))
        lines = []

        # Cursor indicator above band
        if self.is_selected:
            lines.append("[bold #FF6600]  ▼   [/]")
        else:
            lines.append("      ")

        for i in range(6, -7, -1):
            if i == 0:
                marker = "─"
            elif (display_val > 0 and 0 < i <= display_val):
                marker = "█"
            elif (display_val < 0 and display_val <= i < 0):
                marker = "█"
            else:
                marker = "·"

            if i == display_val and display_val != 0:
                color = "#FF6600"
            elif marker == "█":
                color = "#FF8833" if display_val > 0 else "#3388FF"
            elif marker == "─":
                color = "#666666"
            else:
                color = "#333333"

            db_label = f"{i*2:+3d}" if i % 3 == 0 else "   "
            lines.append(f"[{color}]{db_label} {marker}[/]")

        if self.is_selected:
            lines.append(f"[bold black on #FF6600]{self.freq_label:^6}[/]")
            lines.append(f"[bold white]{self.value:+d}dB[/]")
        else:
            lines.append(f"[bold #FF6600]{self.freq_label:^6}[/]")
            lines.append(f"[dim]{self.value:+d}dB[/]")

        bar.update(Text.from_markup("\n".join(lines)))

    def adjust(self, delta: int):
        new_val = max(-12, min(12, self.value + delta))
        if new_val != self.value:
            self.value = new_val
            # Update controller
            bands = list(self.controller.state.eq_bands)
            bands[self.band_index] = new_val
            self.controller.set_eq_bands(bands)


class EQWidget(Static):
    """Adaptive graphical equalizer (3-band, 5-band, 10-band) with capability gating."""

    selected_band: reactive[int] = reactive(0)

    def __init__(self, controller: HeadsetController, **kwargs):
        super().__init__(**kwargs)
        self.controller = controller
        self.bands: list[EQBandSlider] = []
        self.selected_band = 0

    def compose(self) -> ComposeResult:
        yield Static(id="eq-header")
        self.bands = []
        with Horizontal(id="eq-bands-container"):
            for i in range(10):
                band = EQBandSlider(i, f"B{i+1}", self.controller, id=f"eq-band-{i}")
                self.bands.append(band)
                yield band
        yield Static(id="eq-presets-label")
        with Horizontal(id="eq-preset-buttons"):
            yield Button("Flat", id="eq-flat", variant="default")
            yield Button("Jazz", id="eq-jazz", variant="default")
            yield Button("Vocal", id="eq-vocal", variant="default")
            yield Button("Bass", id="eq-bass", variant="default")
            yield Button("Club", id="eq-club", variant="default")
        yield Static("[dim italic]  Equalizer tuning is not supported on this model.[/]", id="eq-unsupported")

    def on_mount(self):
        self._update_presets_label()
        self.update_capabilities(self.controller.state.profile)

    def update_capabilities(self, profile):
        """Update visible EQ band sliders and presets per model capability."""
        freqs = profile.eq_band_frequencies
        has_eq = (profile.eq_type.value != "none" and bool(freqs))

        try:
            bands_container = self.query_one("#eq-bands-container", Horizontal)
            presets_label = self.query_one("#eq-presets-label", Static)
            presets_box = self.query_one("#eq-preset-buttons", Horizontal)
            unsupported = self.query_one("#eq-unsupported", Static)
        except NoMatches:
            return

        if not has_eq:
            bands_container.display = False
            presets_label.display = False
            presets_box.display = False
            unsupported.display = True
        else:
            bands_container.display = True
            unsupported.display = False
            presets_label.display = bool(profile.eq_presets)
            presets_box.display = bool(profile.eq_presets)

            num_bands = len(freqs)
            for i, band in enumerate(self.bands):
                if i < num_bands:
                    band.display = True
                    band.freq_label = freqs[i]
                    band._render_bar()
                else:
                    band.display = False

            if self.selected_band >= num_bands:
                self.selected_band = max(0, num_bands - 1)
            for i, band in enumerate(self.bands):
                if i < num_bands:
                    band.is_selected = (i == self.selected_band)
                else:
                    band.is_selected = False

        self._update_header()

    def select_band(self, index: int) -> int:
        """Select active EQ band slider."""
        freqs = self.controller.state.profile.eq_band_frequencies
        num_bands = len(freqs)
        if not self.bands or num_bands == 0:
            return 0
        new_index = max(0, min(num_bands - 1, index))
        self.selected_band = new_index
        for i, band in enumerate(self.bands):
            band.is_selected = (i == new_index and i < num_bands)
        self._update_header()
        return self.selected_band

    def adjust_selected_band(self, delta: int) -> int:
        """Adjust gain of selected EQ band slider."""
        num_bands = len(self.controller.state.profile.eq_band_frequencies)
        if not self.bands or not (0 <= self.selected_band < min(len(self.bands), num_bands)):
            return 0
        self.bands[self.selected_band].adjust(delta)
        self._update_header()
        return self.bands[self.selected_band].value

    def _update_header(self):
        try:
            header = self.query_one("#eq-header", Static)
        except NoMatches:
            return
        if not self.controller.state.profile.eq_band_frequencies or self.controller.state.profile.eq_type.value == "none":
            header.update(Text.from_markup(
                "[bold #FF6600]🎚️ EQUALIZER[/]  [dim]» Not supported[/]"
            ))
            return
        preset = self.controller.state.eq_preset_name
        active_freq = ""
        if self.bands and 0 <= self.selected_band < len(self.bands):
            active_freq = f" · Band: [bold yellow]{self.bands[self.selected_band].freq_label}[/]"
        header.update(Text.from_markup(
            f"[bold #FF6600]🎚️ EQUALIZER[/]  [bold white]» {preset}[/]{active_freq}  "
            f"[dim](A/D: select band · W/S: ±gain · Ctrl+S: save)[/]"
        ))

    def _update_presets_label(self):
        try:
            label = self.query_one("#eq-presets-label", Static)
            label.update(Text.from_markup("\n[bold #FF6600]Presets:[/]"))
        except NoMatches:
            pass

    def update_bands(self, band_values: list[int]):
        """Update all band sliders from a list of values."""
        num_bands = len(self.controller.state.profile.eq_band_frequencies)
        for i, band in enumerate(self.bands):
            if i < num_bands and i < len(band_values):
                band.value = band_values[i]

    def on_button_pressed(self, event: Button.Pressed) -> None:
        p = self.controller.state.profile
        if p.eq_type.value == "none" or not p.eq_band_frequencies:
            return
        preset_map = {
            "eq-flat": EQPreset.FLAT,
            "eq-jazz": EQPreset.JAZZ,
            "eq-vocal": EQPreset.VOCAL,
            "eq-bass": EQPreset.BASS,
            "eq-club": EQPreset.CLUB,
        }
        preset = preset_map.get(event.button.id)
        if preset is not None:
            self.controller.set_eq_preset(preset)
            self.update_bands(self.controller.state.eq_bands)
            self._update_header()
            # Highlight active preset
            for pid, p_val in preset_map.items():
                try:
                    btn = self.query_one(f"#{pid}", Button)
                    btn.variant = "warning" if p_val == preset else "default"
                except NoMatches:
                    pass


class ActivityLog(Static):
    """Scrollable activity/event log."""

    def compose(self) -> ComposeResult:
        yield Static(id="log-header")
        yield ScrollableContainer(
            Static(id="log-content"),
            id="log-scroll",
        )

    def on_mount(self):
        header = self.query_one("#log-header", Static)
        header.update(Text.from_markup("[bold #FF6600]📋 ACTIVITY LOG[/]"))

    def update_log(self, entries: list[str]):
        content = self.query_one("#log-content", Static)
        if not entries:
            content.update(Text.from_markup("[dim]No activity yet...[/]"))
            return

        lines = []
        for entry in entries[-20:]:  # Show last 20
            # Colorize log entries
            if "✓" in entry:
                lines.append(f"[green]{entry}[/]")
            elif "✗" in entry:
                lines.append(f"[red]{entry}[/]")
            elif "⚠" in entry:
                lines.append(f"[yellow]{entry}[/]")
            else:
                lines.append(f"[dim]{entry}[/]")

        content.update(Text.from_markup("\n".join(lines)))


class HealthWidget(Static):
    """Battery health overview panel showing retention, cycles, and confidence."""

    def compose(self) -> ComposeResult:
        yield Static(id="health-header")
        yield Static(id="health-content")

    def on_mount(self):
        try:
            self.query_one("#health-header", Static).update(
                Text.from_markup("[bold #FF6600]🔋 BATTERY HEALTH & RETENTION[/]")
            )
        except NoMatches:
            pass

    def update_health(self, controller: Optional[HeadsetController] = None):
        try:
            content = self.query_one("#health-content", Static)
        except NoMatches:
            return

        if controller is None:
            content.update(Text.from_markup("[dim]No health data loaded.[/]"))
            return

        try:
            tracker = BatteryHealthTracker()
            device_id = controller.state.bt_address or controller.state.device_name
            report = tracker.get_health_summary(device_id, controller.state.device_name)

            lines = []
            for name, comp in report.components.items():
                conf_color = "red" if comp.confidence == "low" else ("yellow" if comp.confidence == "medium" else "green")
                ret_val = f"{comp.retention_trend_pct:.1f}%" if comp.retention_trend_pct else "N/A"
                rate_val = f"{comp.discharge_rate_pct_per_hr:.1f}%/hr" if comp.discharge_rate_pct_per_hr else "N/A"
                lines.append(
                    f"[bold white]{name.capitalize()}:[/] {comp.current_level}% "
                    f"│ Cycles: [yellow]{comp.estimated_cycles:.1f} EFC[/] "
                    f"│ Retention: [magenta]{ret_val}[/]"
                )
                lines.append(f"  [dim]• Rate:[/] {rate_val} │ [dim]Confidence:[/] [{conf_color}]{comp.confidence.upper()}[/]")
                lines.append(f"  [dim italic]{comp.note}[/]")
            content.update(Text.from_markup("\n".join(lines)))
        except Exception as e:
            content.update(Text.from_markup(f"[red]Health error:[/] {e}"))


class StatusBar(Static):
    """Bottom status bar with quick info."""

    def compose(self) -> ComposeResult:
        yield Static(id="status-content")

    def update_status(self, state: HeadsetState, simulating: bool):
        try:
            content = self.query_one("#status-content", Static)
        except NoMatches:
            return
        sim_tag = "[bold yellow] SIM [/]" if simulating else ""
        conn = "[green]●[/]" if state.connected else "[red]●[/]"
        batt = f"{state.battery_level}%" if state.battery_level >= 0 else "?"

        content.update(Text.from_markup(
            f" {conn} {state.device_name}  │  "
            f"🔋 {batt}  │  "
            f"🔇 {state.noise_mode_name}  │  "
            f"🎚️ {state.eq_preset_name}"
            f"  {sim_tag}"
        ))


# ─── Main App ────────────────────────────────────────────────────────────────

class JBLPcApp(App):
    """JBLPc — Universal JBL Controller TUI."""

    TITLE = "JBLPc — Universal JBL Controller"
    SUB_TITLE = "Terminal Edition"

    CSS = """
    Screen {
        background: #0a0a0a;
    }

    BrandBanner {
        height: 5;
        margin: 0 1;
    }

    #main-layout {
        height: 1fr;
        margin: 0 1;
    }

    #left-panel {
        width: 1fr;
        min-width: 30;
        margin-right: 1;
    }

    #right-panel {
        width: 2fr;
        min-width: 50;
    }

    BatteryWidget {
        height: 4;
        border: solid #333333;
        padding: 0 1;
        margin-bottom: 1;
    }

    HealthWidget {
        height: auto;
        border: solid #333333;
        padding: 0 1;
        margin-bottom: 1;
    }

    #health-header {
        height: 1;
    }

    #health-content {
        height: auto;
    }

    NoiseControlWidget {
        height: auto;
        border: solid #333333;
        padding: 0 1;
        margin-bottom: 1;
    }

    #noise-header {
        height: 2;
    }

    #noise-buttons {
        height: 3;
        align-horizontal: center;
    }

    #noise-buttons Button {
        margin: 0 1;
        min-width: 10;
    }

    EQWidget {
        height: auto;
        border: solid #333333;
        padding: 0 1;
        margin-bottom: 1;
    }

    #eq-header {
        height: 2;
    }

    #eq-bands-container {
        height: auto;
        align-horizontal: center;
    }

    EQBandSlider {
        width: 8;
        height: auto;
        margin: 0 0;
    }

    #eq-presets-label {
        height: 2;
    }

    #eq-preset-buttons {
        height: 3;
        align-horizontal: center;
    }

    #eq-preset-buttons Button {
        margin: 0 1;
        min-width: 8;
    }

    ActivityLog {
        height: 1fr;
        border: solid #333333;
        padding: 0 1;
    }

    #log-header {
        height: 2;
    }

    #log-scroll {
        height: 1fr;
        max-height: 15;
    }

    StatusBar {
        dock: bottom;
        height: 1;
        background: #1a1a1a;
        border-top: solid #333333;
    }

    #connection-buttons {
        height: 3;
        align-horizontal: center;
        margin-bottom: 1;
    }

    #connection-buttons Button {
        margin: 0 1;
    }

    Button {
        background: #222222;
        color: #cccccc;
        border: solid #444444;
    }

    Button:hover {
        background: #333333;
        border: solid #FF6600;
    }

    Button.-warning {
        background: #FF6600;
        color: #000000;
        border: solid #FF8833;
    }

    Header {
        background: #FF6600;
        color: #000000;
    }

    Footer {
        background: #1a1a1a;
    }
    """

    BINDINGS = [
        Binding("q", "quit", "Quit", show=True),
        Binding("c", "connect", "Connect", show=True),
        Binding("x", "disconnect", "Disconnect", show=True),
        Binding("n", "cycle_noise", "Cycle ANC", show=True),
        Binding("e", "cycle_eq", "Cycle EQ", show=True),
        Binding("h", "toggle_health", "Health", show=True),
        Binding("w", "eq_gain_up", "EQ Gain +", show=True),
        Binding("s", "eq_gain_down", "EQ Gain -", show=True),
        Binding("a", "eq_band_prev", "EQ Band ←", show=True),
        Binding("d", "eq_band_next", "EQ Band →", show=True),
        Binding("up", "eq_gain_up", "EQ Gain +", show=False),
        Binding("down", "eq_gain_down", "EQ Gain -", show=False),
        Binding("left", "eq_band_prev", "EQ Band ←", show=False),
        Binding("right", "eq_band_next", "EQ Band →", show=False),
        Binding("ctrl+s", "save_eq", "Save EQ", show=True),
        Binding("1", "noise_off", "Noise Off", show=False),
        Binding("2", "noise_anc", "ANC", show=False),
        Binding("3", "noise_ambient", "Ambient", show=False),
        Binding("4", "noise_talkthru", "TalkThru", show=False),
        Binding("b", "check_battery", "Battery", show=True),
        Binding("p", "power_off", "Power Off", show=True),
        Binding("m", "toggle_simulation", "Sim Mode", show=True),
        Binding("r", "refresh", "Refresh", show=True),
    ]

    def __init__(self, controller: HeadsetController, **kwargs):
        super().__init__(**kwargs)
        self.controller = controller
        self._refresh_timer: Optional[Timer] = None

    def compose(self) -> ComposeResult:
        yield Header()
        yield BrandBanner()
        with Horizontal(id="connection-buttons"):
            yield Button("⚡ Connect", id="btn-connect", variant="warning")
            yield Button("Disconnect", id="btn-disconnect")
            yield Button("🔍 Scan", id="btn-scan")
            yield Button("⏻ Power Off", id="btn-poweroff")
            yield Button("🧪 Simulation", id="btn-simulate")
        with Horizontal(id="main-layout"):
            with Vertical(id="left-panel"):
                yield BatteryWidget()
                yield HealthWidget()
                yield NoiseControlWidget(self.controller)
                yield ActivityLog()
            with Vertical(id="right-panel"):
                yield EQWidget(self.controller)
        yield StatusBar()
        yield Footer()

    def on_mount(self):
        """Set up initial state and auto-refresh."""
        self.title = f"TuneDeck — {self.controller.state.device_name}"
        self.controller.add_listener(self._on_state_change)

        # Check terminal size
        try:
            size = self.console.size
            if size.width < 45 or size.height < 14:
                self.notify("Terminal size is small. Layout may be compressed.", severity="warning")
        except (AttributeError, ValueError) as e:
            self.log.warning(f"Could not check console dimensions: {e}")

        # Auto-connect if address is configured or in simulation mode
        if self.controller.simulating:
            self.controller.connect()
        elif self.controller.state.bt_address:
            connected = self.controller.connect()
            if not connected:
                self.controller._add_log(f"⚠ Could not connect to {self.controller.state.bt_address}: {self.controller.last_error or 'Device unreachable'}")
        else:
            self.controller._add_log("⚠ No paired JBL device detected. Press 'Scan' or '🧪 Simulation'.")

        self._update_all()

        # Periodic refresh
        self._refresh_timer = self.set_interval(2.0, self._periodic_refresh)

    def _on_state_change(self, state: HeadsetState):
        """Called when controller state changes."""
        self._update_all()

    def _update_all(self):
        """Update all widgets from controller state."""
        state = self.controller.state

        try:
            self.query_one(BrandBanner).update_state(state, simulating=self.controller.simulating)
        except NoMatches:
            pass

        try:
            sim_btn = self.query_one("#btn-simulate", Button)
            if self.controller.simulating:
                sim_btn.label = "🔌 Hardware"
                sim_btn.variant = "warning"
            else:
                sim_btn.label = "🧪 Simulation"
                sim_btn.variant = "default"
        except NoMatches:
            pass

        try:
            self.query_one(BatteryWidget).update_battery(state.battery_level, state=state)
        except NoMatches:
            pass

        try:
            self.query_one(HealthWidget).update_health(self.controller)
        except NoMatches:
            pass

        try:
            power_btn = self.query_one("#btn-poweroff", Button)
            power_btn.display = state.profile.has_power_off_command
        except NoMatches:
            pass

        try:
            noise_widget = self.query_one(NoiseControlWidget)
            noise_widget.update_capabilities(state.profile)
            noise_widget.current_mode = state.noise_mode
        except NoMatches:
            pass

        try:
            eq_widget = self.query_one(EQWidget)
            eq_widget.update_capabilities(state.profile)
            eq_widget.update_bands(state.eq_bands)
        except NoMatches:
            pass

        try:
            self.query_one(ActivityLog).update_log(self.controller.get_log())
        except NoMatches:
            pass

        try:
            self.query_one(StatusBar).update_status(state, self.controller.simulating)
        except NoMatches:
            pass

    def _periodic_refresh(self):
        """Periodic state refresh."""
        if self.controller.state.connected:
            if self.controller.simulating:
                self.controller.get_battery()
            else:
                self.controller.poll()
                self.controller._query_battery()
            # Log reading to health database
            self.controller.log_health_reading()
            try:
                self.query_one(HealthWidget).update_health(self.controller)
            except NoMatches:
                pass

    def action_toggle_health(self):
        """Toggle Health widget visibility."""
        try:
            hw = self.query_one(HealthWidget)
            hw.display = not hw.display
        except NoMatches:
            pass

    # ─── Button handlers ─────────────────────────────────────────────────

    def on_button_pressed(self, event: Button.Pressed) -> None:
        btn_id = event.button.id

        if btn_id == "btn-connect":
            self.controller.connect()
        elif btn_id == "btn-disconnect":
            self.controller.disconnect()
        elif btn_id == "btn-scan":
            devices = self.controller.discover_devices()
            if devices:
                for d in devices:
                    self.controller._add_log(f"🔍 Found: {d['name']} ({d['address']})")
                if not self.controller.state.bt_address and devices:
                    self.controller.state.bt_address = devices[0]["address"]
                    try:
                        from ..protocol import save_config, load_config
                        cfg = load_config()
                        cfg["bluetooth_address"] = devices[0]["address"]
                        save_config(cfg)
                    except Exception as err:
                        pass_err = str(err)
                    self.controller.connect()
            else:
                self.controller._add_log("🔍 No JBL devices found (is BT on?)")
            self._update_all()
        elif btn_id == "btn-poweroff":
            if not self.controller.state.profile.has_power_off_command:
                self.notify("Power off is not supported on this model.", severity="warning")
                return
            self.controller.power_off()
        elif btn_id == "btn-simulate":
            self.action_toggle_simulation()

    # ─── Key bindings ────────────────────────────────────────────────────

    def action_connect(self):
        self.controller.connect()

    def action_disconnect(self):
        self.controller.disconnect()

    def action_eq_gain_up(self):
        p = self.controller.state.profile
        if p.eq_type.value == "none" or not p.eq_band_frequencies:
            self.notify("Equalizer is not supported on this model.", severity="warning")
            return
        try:
            eq = self.query_one(EQWidget)
            eq.adjust_selected_band(1)
        except NoMatches:
            pass

    def action_eq_gain_down(self):
        p = self.controller.state.profile
        if p.eq_type.value == "none" or not p.eq_band_frequencies:
            self.notify("Equalizer is not supported on this model.", severity="warning")
            return
        try:
            eq = self.query_one(EQWidget)
            eq.adjust_selected_band(-1)
        except NoMatches:
            pass

    def action_eq_band_prev(self):
        p = self.controller.state.profile
        if p.eq_type.value == "none" or not p.eq_band_frequencies:
            self.notify("Equalizer is not supported on this model.", severity="warning")
            return
        try:
            eq = self.query_one(EQWidget)
            eq.select_band(eq.selected_band - 1)
        except NoMatches:
            pass

    def action_eq_band_next(self):
        p = self.controller.state.profile
        if p.eq_type.value == "none" or not p.eq_band_frequencies:
            self.notify("Equalizer is not supported on this model.", severity="warning")
            return
        try:
            eq = self.query_one(EQWidget)
            eq.select_band(eq.selected_band + 1)
        except NoMatches:
            pass

    def action_save_eq(self):
        p = self.controller.state.profile
        if p.eq_type.value == "none" or not p.eq_band_frequencies:
            self.notify("Equalizer is not supported on this model.", severity="warning")
            return
        success = self.controller.save_eq_to_config()
        if success:
            self.notify("Equalizer settings saved to config.json", title="EQ Saved", severity="information")
        else:
            self.notify(f"Save failed: {self.controller.last_error}", title="Error", severity="error")
        self._update_all()

    def action_cycle_noise(self):
        if not self.controller.state.profile.has_anc:
            self.notify("Noise control is not supported on this model.", severity="warning")
            return
        self.controller.cycle_noise_mode()

    def action_cycle_eq(self):
        p = self.controller.state.profile
        if p.eq_type.value == "none" or not p.eq_band_frequencies:
            self.notify("Equalizer is not supported on this model.", severity="warning")
            return
        self.controller.cycle_eq_preset()

    def action_noise_off(self):
        p = self.controller.state.profile
        if not (p.has_anc or p.has_ambient_aware or p.has_talkthru):
            self.notify("Noise control is not supported on this model.", severity="warning")
            return
        self.controller.set_noise_mode(NoiseMode.OFF)

    def action_noise_anc(self):
        if not self.controller.state.profile.has_anc:
            self.notify("Active Noise Cancellation is not supported on this model.", severity="warning")
            return
        self.controller.set_noise_mode(NoiseMode.ANC)

    def action_noise_ambient(self):
        if not self.controller.state.profile.has_ambient_aware:
            self.notify("Ambient Aware is not supported on this model.", severity="warning")
            return
        self.controller.set_noise_mode(NoiseMode.AMBIENT_AWARE)

    def action_noise_talkthru(self):
        if not self.controller.state.profile.has_talkthru:
            self.notify("TalkThru is not supported on this model.", severity="warning")
            return
        self.controller.set_noise_mode(NoiseMode.TALKTHRU)

    def action_check_battery(self):
        self.controller.get_battery()

    def action_power_off(self):
        if not self.controller.state.profile.has_power_off_command:
            self.notify("Remote power-off is not supported on this model.", severity="warning")
            return
        self.controller.power_off()

    def action_refresh(self):
        if self.controller.state.connected:
            self.controller.get_battery()
        self._update_all()

    def action_toggle_simulation(self):
        """Toggle between real hardware and offline simulator."""
        if not self.controller.simulating:
            self.controller.disconnect()
            self.controller._simulate = True
            self.controller.connect()
            self.controller._add_log("🧪 Switched to Simulation Mode")
            self.notify("Simulation mode activated", title="Mode", severity="information")
        else:
            self.controller.disconnect()
            self.controller._simulate = False
            self.controller.state.connected = False
            self.controller._add_log("🔌 Switched to Hardware Mode")
            if self.controller.state.bt_address:
                self.controller.connect()
            self.notify("Hardware mode activated", title="Mode", severity="information")
        self._update_all()


def run_tui(controller: HeadsetController):
    """Launch the TUI application."""
    app = JBLPcApp(controller)
    app.run()


# TuneDeck project alias
TuneDeckApp = JBLPcApp

