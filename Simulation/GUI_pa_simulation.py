from __future__ import annotations

from dataclasses import dataclass
import os
import queue
import subprocess
import sys
import threading
from datetime import date, datetime
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext, ttk

SIMULATION_DIR = Path(__file__).resolve().parent
ROOT_DIR = SIMULATION_DIR.parent
if str(SIMULATION_DIR) not in sys.path:
    sys.path.append(str(SIMULATION_DIR))

from dotenv import load_dotenv

ENV_PATH = SIMULATION_DIR / ".env"
load_dotenv(ENV_PATH)

from run_full_pa_simulation import DEFAULT_OUTPUT_DIR  # noqa: E402
from run_llm_pa_decision import LLM1_MAX_TOKENS, LLM2_MAX_TOKENS, MODEL_NAME, TEMPERATURE, TOP_P  # noqa: E402
from state_assessment import DEFAULT_MAX_TOKENS as STATE_ASSESSMENT_MAX_TOKENS  # noqa: E402

SUPPORTED_MODELS = (MODEL_NAME,)
DEFAULTS: dict[str, object] = {
    "n_personas": "2",
    "n_days": "2",
    "start_date": "2026-01-01",
    "base_seed": "137",
    "output_dir": str(DEFAULT_OUTPUT_DIR),
    "model": MODEL_NAME,
    "temperature": str(TEMPERATURE),
    "top_p": str(TOP_P),
    "llm_seed": "137",
    "llm1_max_tokens": str(LLM1_MAX_TOKENS),
    "llm2_max_tokens": str(LLM2_MAX_TOKENS),
    "state_assessment_max_tokens": str(STATE_ASSESSMENT_MAX_TOKENS),
    "dry_run": False,
    "enable_resource_tracking": True,
    "enable_codecarbon": True,
    "verbose_llm_debug": False,
    "include_full_hourly_context": False,
    "state_assessment_json_mode": False,
    "physical_activity_hours_per_week": "",
    "social_hours_per_week": "",
    "care_work_hours_per_week": "",
    "work_hours_per_week": "",
    "workplace_distance_km": "",
    "indoor_activity_distance_km": "",
    "outdoor_activity_distance_km": "",
}


class GUIValidationError(ValueError):
    """Validation error with field metadata for GUI feedback."""

    def __init__(self, field_name: str, entered: str, expected: str, example: str | None = None, extra: str | None = None) -> None:
        self.field_name = field_name
        self.entered = entered
        self.expected = expected
        self.example = example
        self.extra = extra
        lines = [f"Ungültige Eingabe bei „{field_name}“.", "", f"Eingegeben: {entered if entered else '(leer)'}", f"Erwartet: {expected}"]
        if example:
            lines.append(f"Beispiel: {example}")
        if extra:
            lines.extend(["", extra])
        super().__init__("\n".join(lines))


@dataclass(frozen=True)
class ValidatedConfig:
    n_personas: int
    n_days: int
    start_date: date
    base_seed: int
    output_dir: Path
    model: str
    temperature: float
    top_p: float
    llm_seed: int | None
    llm1_max_tokens: int
    llm2_max_tokens: int
    state_assessment_max_tokens: int
    dry_run: bool
    enable_resource_tracking: bool
    enable_codecarbon: bool
    verbose_llm_debug: bool
    include_full_hourly_context: bool
    state_assessment_json_mode: bool
    physical_activity_hours_per_week: list[float] | None
    social_hours_per_week: list[float] | None
    care_work_hours_per_week: list[float] | None
    work_hours_per_week: list[float] | None
    workplace_distance_km: list[float] | None
    indoor_activity_distance_km: list[float] | None
    outdoor_activity_distance_km: list[float] | None


def parse_required_int(value: str, field_name: str, minimum: int | None = None) -> int:
    raw = value.strip()
    if not raw:
        raise GUIValidationError(field_name, raw, "ganze Zahl", "1")
    try:
        parsed = int(raw)
    except ValueError as exc:
        raise GUIValidationError(field_name, raw, "ganze Zahl ohne Dezimalstellen", "1") from exc
    if minimum is not None and parsed < minimum:
        raise GUIValidationError(field_name, raw, f"ganze Zahl ≥ {minimum}", str(minimum))
    return parsed


def parse_required_float(value: str, field_name: str, minimum: float | None = None, maximum: float | None = None, minimum_inclusive: bool = True) -> float:
    raw = value.strip()
    if not raw:
        raise GUIValidationError(field_name, raw, "Dezimalzahl mit Punkt als Dezimaltrennzeichen", "0")
    if "," in raw:
        raise GUIValidationError(field_name, raw, "Dezimalzahl mit Punkt als Dezimaltrennzeichen", raw.replace(",", "."), "Bitte Dezimalpunkte verwenden.")
    try:
        parsed = float(raw)
    except ValueError as exc:
        raise GUIValidationError(field_name, raw, "Dezimalzahl mit Punkt als Dezimaltrennzeichen", "0.5") from exc
    if minimum is not None and (parsed < minimum or (parsed == minimum and not minimum_inclusive)):
        op = "mindestens" if minimum_inclusive else "grösser als"
        raise GUIValidationError(field_name, raw, f"Dezimalzahl {op} {minimum:g}" + (f" und höchstens {maximum:g}" if maximum is not None else ""), "0.5")
    if maximum is not None and parsed > maximum:
        lower = "" if minimum is None else (f"grösser als {minimum:g} und " if not minimum_inclusive else f"mindestens {minimum:g} und ")
        raise GUIValidationError(field_name, raw, f"Dezimalzahl {lower}höchstens {maximum:g}", "1")
    return parsed


def parse_required_date(value: str, field_name: str) -> date:
    raw = value.strip()
    if not raw:
        raise GUIValidationError(field_name, raw, "YYYY-MM-DD", "2026-03-02")
    try:
        return date.fromisoformat(raw)
    except ValueError as exc:
        raise GUIValidationError(field_name, raw, "YYYY-MM-DD", "2026-03-02") from exc


def validate_model_name(value: str, field_name: str, supported_models: tuple[str, ...] = SUPPORTED_MODELS) -> str:
    raw = value.strip()
    if not raw:
        raise GUIValidationError(field_name, raw, "unterstützter Modellname", supported_models[0] if supported_models else None)
    if supported_models and raw not in supported_models:
        raise GUIValidationError(field_name, raw, "unterstützter Modellname", supported_models[0])
    return raw


def validate_optional_numeric_list(value: str, field_name: str, n_personas: int) -> list[float] | None:
    raw = value.strip()
    if not raw:
        return None
    if ";" in raw:
        raise GUIValidationError(field_name, raw, "eine nicht-negative Zahl oder eine komma-getrennte Liste ohne leere Einträge", "7.5 oder 7.5,5,3")
    parts = [part.strip() for part in raw.split(",")]
    if any(part == "" for part in parts):
        raise GUIValidationError(field_name, raw, "eine nicht-negative Zahl oder eine komma-getrennte Liste ohne leere Einträge", "7.5 oder 7.5,5,3")
    if len(parts) == 2 and all(part.isdigit() for part in parts):
        raise GUIValidationError(field_name, raw, "Dezimalpunkte statt Dezimalkommas; Kommas nur zwischen Personas", f"{parts[0]}.{parts[1]}", "Bitte Dezimalpunkte verwenden. Beispiel: 7.5 statt 7,5.\nKommas trennen die Werte verschiedener Personas.")
    if len(parts) > n_personas:
        raise GUIValidationError(field_name, raw, f"höchstens {n_personas} Wert(e): eine Zahl für alle Personas oder eine komma-getrennte Liste pro Persona", "7.5 oder 7.5,5,3")
    parsed: list[float] = []
    for part in parts:
        try:
            number = float(part)
        except ValueError as exc:
            raise GUIValidationError(field_name, raw, "eine nicht-negative Zahl oder eine komma-getrennte Liste mit Dezimalpunkten", "7.5 oder 7.5,5,3") from exc
        if number < 0:
            raise GUIValidationError(field_name, raw, "nur nicht-negative Werte (≥ 0)", "7.5 oder 7.5,5,3")
        parsed.append(number)
    return parsed


def validate_output_dir(value: str, field_name: str) -> Path:
    raw = value.strip()
    if not raw:
        raise GUIValidationError(field_name, raw, "existierender oder neu anzulegender Ordner", str(DEFAULT_OUTPUT_DIR))
    path = Path(raw).expanduser()
    if path.exists() and not path.is_dir():
        raise GUIValidationError(field_name, raw, "Pfad zu einem Ordner, nicht zu einer Datei", str(DEFAULT_OUTPUT_DIR))
    return path


class PASimulationGUI:
    """Tkinter frontend for the full PA simulation runner."""

    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("PA Simulation GUI")
        self.root.geometry("950x800")
        self.root.minsize(800, 650)
        self.process: subprocess.Popen[str] | None = None
        self.is_running = False
        self.stop_requested = False
        self.output_queue: queue.Queue[tuple[str, str | int | None]] = queue.Queue()
        self.vars: dict[str, tk.Variable] = {}
        self.widgets: dict[str, tk.Widget] = {}
        self._build_ui()
        self.root.after(100, self._process_output_queue)

    def _build_ui(self) -> None:
        container = ttk.Frame(self.root)
        container.pack(fill="both", expand=True)
        canvas = tk.Canvas(container, highlightthickness=0)
        scrollbar = ttk.Scrollbar(container, orient="vertical", command=canvas.yview)
        self.scrollable_frame = ttk.Frame(canvas)
        window_id = canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        self.scrollable_frame.bind("<Configure>", lambda _e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.bind("<Configure>", lambda e: canvas.itemconfigure(window_id, width=e.width))
        self._bind_mousewheel(canvas)

        frame = self.scrollable_frame
        row = 0
        ttk.Label(frame, text="PA Simulation", font=("TkDefaultFont", 14, "bold")).grid(row=row, column=0, columnspan=3, sticky="w", pady=8)
        row += 1
        ttk.Label(frame, text="Grundparameter", font=("TkDefaultFont", 11, "bold")).grid(row=row, column=0, columnspan=3, sticky="w", pady=(10, 4)); row += 1
        row = self._add_entry(frame, row, "Anzahl Personas (ganze Zahl ≥ 1)", "n_personas")
        row = self._add_entry(frame, row, "Anzahl Tage (ganze Zahl ≥ 1)", "n_days")
        row = self._add_entry(frame, row, "Startdatum (YYYY-MM-DD, z. B. 2026-03-02)", "start_date")
        row = self._add_entry(frame, row, "Basis-Seed (ganze Zahl ≥ 0)", "base_seed")
        row = self._add_entry(frame, row, "Output-Pfad (existierender oder neu anzulegender Ordner)", "output_dir", browse=True)

        ttk.Label(frame, text="LLM-Parameter", font=("TkDefaultFont", 11, "bold")).grid(row=row, column=0, columnspan=3, sticky="w", pady=(10, 4)); row += 1
        row = self._add_model_combo(frame, row)
        row = self._add_entry(frame, row, "Temperature (Dezimalzahl von 0 bis 2, z. B. 0)", "temperature")
        row = self._add_entry(frame, row, "Top P (Dezimalzahl > 0 bis 1, z. B. 1)", "top_p")
        row = self._add_entry(frame, row, "LLM-Seed (optional, ganze Zahl ≥ 0)", "llm_seed")
        row = self._add_entry(frame, row, "LLM1 Max Tokens (ganze Zahl ≥ 1)", "llm1_max_tokens")
        row = self._add_entry(frame, row, "LLM2 Max Tokens (ganze Zahl ≥ 1)", "llm2_max_tokens")
        row = self._add_entry(frame, row, "State Assessment Max Tokens (ganze Zahl ≥ 1)", "state_assessment_max_tokens")

        ttk.Label(frame, text="Verhaltensparameter (optional)", font=("TkDefaultFont", 11, "bold")).grid(row=row, column=0, columnspan=3, sticky="w", pady=(10, 4))
        row += 1
        for label, key in (("PA-Stunden pro Woche (≥ 0; einzelne Zahl oder Liste, z. B. 7.5 oder 7.5,5,3)", "physical_activity_hours_per_week"), ("Soziale Stunden pro Woche (≥ 0; einzelne Zahl oder Liste)", "social_hours_per_week"), ("Care-Arbeit pro Woche (≥ 0; einzelne Zahl oder Liste)", "care_work_hours_per_week"), ("Arbeitsstunden pro Woche (≥ 0; einzelne Zahl oder Liste)", "work_hours_per_week")):
            row = self._add_entry(frame, row, label, key)

        ttk.Label(frame, text="POI-Entfernungen", font=("TkDefaultFont", 11, "bold")).grid(row=row, column=0, columnspan=3, sticky="w", pady=(10, 4))
        row += 1
        for label, key in (("Arbeitsplatz-Entfernung in km (≥ 0; einzelne Zahl oder Liste)", "workplace_distance_km"), ("Indoor-Aktivitätsentfernung in km (≥ 0; einzelne Zahl oder Liste)", "indoor_activity_distance_km"), ("Outdoor-Aktivitätsentfernung in km (≥ 0; einzelne Zahl oder Liste)", "outdoor_activity_distance_km")):
            row = self._add_entry(frame, row, label, key)

        for label, key in (("Dry run", "dry_run"), ("Resource tracking", "enable_resource_tracking"), ("CodeCarbon", "enable_codecarbon"), ("Verbose LLM debugging", "verbose_llm_debug"), ("Full hourly context", "include_full_hourly_context"), ("State Assessment JSON mode", "state_assessment_json_mode")):
            var = tk.BooleanVar(value=bool(DEFAULTS[key])); self.vars[key] = var
            ttk.Checkbutton(frame, text=label, variable=var).grid(row=row, column=0, columnspan=2, sticky="w", pady=2)
            row += 1

        buttons = ttk.Frame(frame); buttons.grid(row=row, column=0, columnspan=3, sticky="ew", pady=8)
        self.start_button = ttk.Button(buttons, text="Start", command=self.start_simulation); self.start_button.pack(side="left", padx=3)
        self.stop_button = ttk.Button(buttons, text="Stop", command=self.stop_simulation, state="disabled"); self.stop_button.pack(side="left", padx=3)
        ttk.Button(buttons, text="Reset defaults", command=self.reset_to_defaults).pack(side="left", padx=3)
        row += 1
        self.output_text = scrolledtext.ScrolledText(frame, height=18, state="disabled")
        self.output_text.grid(row=row, column=0, columnspan=3, sticky="nsew", pady=6)
        frame.columnconfigure(1, weight=1); frame.rowconfigure(row, weight=1)

    def _bind_mousewheel(self, canvas: tk.Canvas) -> None:
        canvas.bind_all("<MouseWheel>", lambda e: canvas.yview_scroll(int(-1 * (e.delta / 120)), "units"))
        canvas.bind_all("<Button-4>", lambda _e: canvas.yview_scroll(-1, "units"))
        canvas.bind_all("<Button-5>", lambda _e: canvas.yview_scroll(1, "units"))

    def _add_entry(self, parent: ttk.Frame, row: int, label: str, key: str, browse: bool = False) -> int:
        ttk.Label(parent, text=label).grid(row=row, column=0, sticky="w", padx=4, pady=2)
        var = tk.StringVar(value=str(DEFAULTS[key])); self.vars[key] = var
        entry = ttk.Entry(parent, textvariable=var)
        entry.grid(row=row, column=1, sticky="ew", padx=4, pady=2)
        self.widgets[key] = entry
        if browse:
            ttk.Button(parent, text="Browse", command=lambda: self._browse_dir(key)).grid(row=row, column=2, padx=4)
        return row + 1

    def _add_model_combo(self, parent: ttk.Frame, row: int) -> int:
        ttk.Label(parent, text="Modell (unterstützter Modellname)").grid(row=row, column=0, sticky="w", padx=4, pady=2)
        var = tk.StringVar(value=str(DEFAULTS["model"])); self.vars["model"] = var
        combo = ttk.Combobox(parent, textvariable=var, values=SUPPORTED_MODELS, state="readonly")
        combo.grid(row=row, column=1, sticky="ew", padx=4, pady=2)
        self.widgets["model"] = combo
        return row + 1

    def _browse_dir(self, key: str) -> None:
        selected = filedialog.askdirectory(initialdir=str(self.vars[key].get() or SIMULATION_DIR))
        if selected:
            self.vars[key].set(selected)

    def reset_to_defaults(self) -> None:
        for key, value in DEFAULTS.items():
            self.vars[key].set(value)

    def queue_output(self, message: str) -> None:
        self.output_queue.put(("output", message))

    def _process_output_queue(self) -> None:
        while True:
            try:
                kind, payload = self.output_queue.get_nowait()
            except queue.Empty:
                break
            if kind == "output":
                self.output_text.config(state="normal")
                self.output_text.insert("end", str(payload))
                self.output_text.see("end")
                self.output_text.config(state="disabled")
            elif kind == "done":
                self._finish_run(int(payload or 0))
            elif kind == "error":
                messagebox.showerror("Simulation error", str(payload))
        self.root.after(100, self._process_output_queue)

    def _finish_run(self, return_code: int) -> None:
        if not self.stop_requested:
            self.queue_output(f"\nProcess finished with return code {return_code}.\n")
        self.is_running = False; self.process = None; self.stop_requested = False
        self.start_button.config(state="normal"); self.stop_button.config(state="disabled")

    def validate_inputs(self) -> ValidatedConfig | None:
        try:
            n_personas = parse_required_int(str(self.vars["n_personas"].get()), "Anzahl Personas", 1)
            n_days = parse_required_int(str(self.vars["n_days"].get()), "Anzahl Tage", 1)
            base_seed = parse_required_int(str(self.vars["base_seed"].get()), "Basis-Seed", 0)
            start_date = parse_required_date(str(self.vars["start_date"].get()), "Startdatum")
            output_dir = validate_output_dir(str(self.vars["output_dir"].get()), "Output-Pfad")
            model = validate_model_name(str(self.vars["model"].get()), "Modell")
            temperature = parse_required_float(str(self.vars["temperature"].get()), "Temperature", 0, 2, True)
            top_p = parse_required_float(str(self.vars["top_p"].get()), "Top P", 0, 1, False)
            llm_seed_raw = str(self.vars["llm_seed"].get()).strip()
            llm_seed = parse_required_int(llm_seed_raw, "LLM-Seed", 0) if llm_seed_raw else None
            llm1_max_tokens = parse_required_int(str(self.vars["llm1_max_tokens"].get()), "LLM1 Max Tokens", 1)
            llm2_max_tokens = parse_required_int(str(self.vars["llm2_max_tokens"].get()), "LLM2 Max Tokens", 1)
            state_assessment_max_tokens = parse_required_int(str(self.vars["state_assessment_max_tokens"].get()), "State Assessment Max Tokens", 1)
            return ValidatedConfig(
                n_personas=n_personas,
                n_days=n_days,
                start_date=start_date,
                base_seed=base_seed,
                output_dir=output_dir,
                model=model,
                temperature=temperature,
                top_p=top_p,
                llm_seed=llm_seed,
                llm1_max_tokens=llm1_max_tokens,
                llm2_max_tokens=llm2_max_tokens,
                state_assessment_max_tokens=state_assessment_max_tokens,
                dry_run=bool(self.vars["dry_run"].get()),
                enable_resource_tracking=bool(self.vars["enable_resource_tracking"].get()),
                enable_codecarbon=bool(self.vars["enable_codecarbon"].get()),
                verbose_llm_debug=bool(self.vars["verbose_llm_debug"].get()),
                include_full_hourly_context=bool(self.vars["include_full_hourly_context"].get()),
                state_assessment_json_mode=bool(self.vars["state_assessment_json_mode"].get()),
                physical_activity_hours_per_week=validate_optional_numeric_list(str(self.vars["physical_activity_hours_per_week"].get()), "PA-Stunden pro Woche", n_personas),
                social_hours_per_week=validate_optional_numeric_list(str(self.vars["social_hours_per_week"].get()), "Soziale Stunden pro Woche", n_personas),
                care_work_hours_per_week=validate_optional_numeric_list(str(self.vars["care_work_hours_per_week"].get()), "Care-Arbeit pro Woche", n_personas),
                work_hours_per_week=validate_optional_numeric_list(str(self.vars["work_hours_per_week"].get()), "Arbeitsstunden pro Woche", n_personas),
                workplace_distance_km=validate_optional_numeric_list(str(self.vars["workplace_distance_km"].get()), "Arbeitsplatz-Entfernung in km", n_personas),
                indoor_activity_distance_km=validate_optional_numeric_list(str(self.vars["indoor_activity_distance_km"].get()), "Indoor-Aktivitätsentfernung in km", n_personas),
                outdoor_activity_distance_km=validate_optional_numeric_list(str(self.vars["outdoor_activity_distance_km"].get()), "Outdoor-Aktivitätsentfernung in km", n_personas),
            )
        except GUIValidationError as exc:
            self.is_running = False
            self._focus_invalid_widget(exc.field_name)
            messagebox.showerror("Ungültige Eingabe", str(exc))
            return None

    def _focus_invalid_widget(self, field_name: str) -> None:
        field_to_key = {
            "Anzahl Personas": "n_personas", "Anzahl Tage": "n_days", "Startdatum": "start_date", "Basis-Seed": "base_seed", "Output-Pfad": "output_dir", "Modell": "model", "Temperature": "temperature", "Top P": "top_p", "LLM-Seed": "llm_seed", "LLM1 Max Tokens": "llm1_max_tokens", "LLM2 Max Tokens": "llm2_max_tokens", "State Assessment Max Tokens": "state_assessment_max_tokens", "PA-Stunden pro Woche": "physical_activity_hours_per_week", "Soziale Stunden pro Woche": "social_hours_per_week", "Care-Arbeit pro Woche": "care_work_hours_per_week", "Arbeitsstunden pro Woche": "work_hours_per_week", "Arbeitsplatz-Entfernung in km": "workplace_distance_km", "Indoor-Aktivitätsentfernung in km": "indoor_activity_distance_km", "Outdoor-Aktivitätsentfernung in km": "outdoor_activity_distance_km",
        }
        widget = self.widgets.get(field_to_key.get(field_name, ""))
        if widget is None:
            return
        widget.focus_set()
        try:
            widget.selection_range(0, "end")  # type: ignore[attr-defined]
        except tk.TclError:
            pass

    def build_command(self, config: ValidatedConfig) -> list[str]:
        """Build the command-line command for run_full_pa_simulation.py."""
        simulation_script = SIMULATION_DIR / "run_full_pa_simulation.py"
        cmd = [sys.executable, str(simulation_script)]
        scalar_args = {
            "--n-personas": config.n_personas,
            "--n-days": config.n_days,
            "--start-date": config.start_date.isoformat(),
            "--base-seed": config.base_seed,
            "--output-dir": str(config.output_dir),
            "--model": config.model,
            "--temperature": f"{config.temperature:g}",
            "--top-p": f"{config.top_p:g}",
            "--llm1-max-tokens": config.llm1_max_tokens,
            "--llm2-max-tokens": config.llm2_max_tokens,
            "--state-assessment-max-tokens": config.state_assessment_max_tokens,
        }
        for flag, value in scalar_args.items():
            cmd.extend([flag, str(value)])
        if config.llm_seed is not None:
            cmd.extend(["--llm-seed", str(config.llm_seed)])
        list_args = {
            "--physical-activity-hours-per-week": config.physical_activity_hours_per_week,
            "--social-hours-per-week": config.social_hours_per_week,
            "--care-work-hours-per-week": config.care_work_hours_per_week,
            "--work-hours-per-week": config.work_hours_per_week,
            "--workplace-distance-km": config.workplace_distance_km,
            "--indoor-activity-distance-km": config.indoor_activity_distance_km,
            "--outdoor-activity-distance-km": config.outdoor_activity_distance_km,
        }
        for flag, values in list_args.items():
            if values is not None:
                cmd.extend([flag, ",".join(f"{value:g}" for value in values)])
        if config.dry_run:
            cmd.append("--dry-run")
        cmd.append("--enable-resource-tracking" if config.enable_resource_tracking else "--disable-resource-tracking")
        cmd.append("--enable-codecarbon" if config.enable_codecarbon else "--disable-codecarbon")
        if config.verbose_llm_debug:
            cmd.append("--verbose-llm-debug")
        if config.include_full_hourly_context:
            cmd.append("--include-full-hourly-context")
        if config.state_assessment_json_mode:
            cmd.append("--state-assessment-json-mode")
        return cmd

    def start_simulation(self) -> None:
        if self.is_running:
            messagebox.showwarning("Simulation running", "A simulation is already running.")
            return
        validated = self.validate_inputs()
        if validated is None:
            return
        if not validated.dry_run and not os.environ.get("UNI_LLM_API_KEY"):
            self.is_running = False
            messagebox.showerror("Missing API key", f"UNI_LLM_API_KEY is missing. Add it to {ENV_PATH} or the process environment before starting a real simulation.")
            return
        cmd = self.build_command(validated)
        self.is_running = True; self.stop_requested = False
        self.start_button.config(state="disabled"); self.stop_button.config(state="normal")
        self.queue_output(f"Startzeit: {datetime.now().isoformat(timespec='seconds')}\n")
        self.queue_output("Command: " + " ".join(cmd) + "\n\n")
        threading.Thread(target=self._run_process, args=(cmd,), daemon=True).start()

    def _run_process(self, cmd: list[str]) -> None:
        try:
            self.process = subprocess.Popen(cmd, cwd=str(SIMULATION_DIR), stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding="utf-8", errors="replace", bufsize=1, env=os.environ.copy())
            assert self.process.stdout is not None
            for line in self.process.stdout:
                self.queue_output(line)
            return_code = self.process.wait()
            self.output_queue.put(("done", return_code))
        except Exception as exc:
            self.queue_output(f"\nError while running simulation: {type(exc).__name__}: {exc}\n")
            self.output_queue.put(("done", 1))

    def stop_simulation(self) -> None:
        if self.process is not None and self.is_running:
            self.stop_requested = True
            self.queue_output("\nStopping simulation...\n")
            self.process.terminate()


def main() -> None:
    root = tk.Tk()
    PASimulationGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
