from __future__ import annotations

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
        row = self._add_entry(frame, row, "Personas", "n_personas")
        row = self._add_entry(frame, row, "Days", "n_days")
        row = self._add_entry(frame, row, "Start date (YYYY-MM-DD)", "start_date")
        row = self._add_entry(frame, row, "Base seed", "base_seed")
        row = self._add_entry(frame, row, "Output directory", "output_dir", browse=True)
        row = self._add_model_combo(frame, row)
        row = self._add_entry(frame, row, "Temperature", "temperature")
        row = self._add_entry(frame, row, "Top p", "top_p")
        row = self._add_entry(frame, row, "LLM seed", "llm_seed")
        row = self._add_entry(frame, row, "LLM1 max tokens", "llm1_max_tokens")
        row = self._add_entry(frame, row, "LLM2 max tokens", "llm2_max_tokens")
        row = self._add_entry(frame, row, "State Assessment max tokens", "state_assessment_max_tokens")

        ttk.Label(frame, text="Verhaltensparameter (optional)", font=("TkDefaultFont", 11, "bold")).grid(row=row, column=0, columnspan=3, sticky="w", pady=(10, 4))
        row += 1
        for label, key in (("Physical activity hours/week", "physical_activity_hours_per_week"), ("Social hours/week", "social_hours_per_week"), ("Care work hours/week", "care_work_hours_per_week"), ("Work hours/week", "work_hours_per_week"), ("Workplace distance km", "workplace_distance_km"), ("Indoor activity distance km", "indoor_activity_distance_km"), ("Outdoor activity distance km", "outdoor_activity_distance_km")):
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
        ttk.Entry(parent, textvariable=var).grid(row=row, column=1, sticky="ew", padx=4, pady=2)
        if browse:
            ttk.Button(parent, text="Browse", command=lambda: self._browse_dir(key)).grid(row=row, column=2, padx=4)
        return row + 1

    def _add_model_combo(self, parent: ttk.Frame, row: int) -> int:
        ttk.Label(parent, text="Model").grid(row=row, column=0, sticky="w", padx=4, pady=2)
        var = tk.StringVar(value=str(DEFAULTS["model"])); self.vars["model"] = var
        ttk.Combobox(parent, textvariable=var, values=SUPPORTED_MODELS, state="readonly").grid(row=row, column=1, sticky="ew", padx=4, pady=2)
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

    def _validate_int(self, key: str, label: str, minimum: int) -> int:
        try:
            value = int(str(self.vars[key].get()).strip())
        except ValueError as exc:
            raise ValueError(f"{label} must be an integer.") from exc
        if value < minimum:
            raise ValueError(f"{label} must be >= {minimum}.")
        return value

    def _validate_float(self, key: str, label: str, low: float, high: float, include_low: bool, include_high: bool) -> float:
        try:
            value = float(str(self.vars[key].get()).strip())
        except ValueError as exc:
            raise ValueError(f"{label} must be numeric.") from exc
        if (value < low or (value == low and not include_low)) or (value > high or (value == high and not include_high)):
            raise ValueError(f"{label} must be {'>=' if include_low else '>'} {low} and {'<=' if include_high else '<'} {high}.")
        return value

    def _validate_override(self, key: str, label: str, n_personas: int) -> None:
        raw = str(self.vars[key].get()).strip()
        if not raw:
            return
        parts = [part.strip() for part in raw.split(",")]
        if any(part == "" for part in parts):
            raise ValueError(f"{label} contains an empty list element.")
        if len(parts) > n_personas:
            raise ValueError(f"{label} has more values than personas.")
        for part in parts:
            try:
                value = float(part)
            except ValueError as exc:
                raise ValueError(f"{label} contains a non-numeric value: {part!r}.") from exc
            if value < 0:
                raise ValueError(f"{label} values must be non-negative.")

    def validate_inputs(self) -> bool:
        try:
            n_personas = self._validate_int("n_personas", "Personas", 1)
            self._validate_int("n_days", "Days", 1)
            self._validate_int("base_seed", "Base seed", 0)
            llm_seed = str(self.vars["llm_seed"].get()).strip()
            if llm_seed:
                self._validate_int("llm_seed", "LLM seed", 0)
            self._validate_float("temperature", "Temperature", 0, 2, True, True)
            self._validate_float("top_p", "Top p", 0, 1, False, True)
            for key, label in (("llm1_max_tokens", "LLM1 max tokens"), ("llm2_max_tokens", "LLM2 max tokens"), ("state_assessment_max_tokens", "State Assessment max tokens")):
                self._validate_int(key, label, 1)
            try:
                date.fromisoformat(str(self.vars["start_date"].get()).strip())
            except ValueError as exc:
                raise ValueError("Start date must use ISO format YYYY-MM-DD.") from exc
            for key, label in (("physical_activity_hours_per_week", "Physical activity hours"), ("social_hours_per_week", "Social hours"), ("care_work_hours_per_week", "Care work hours"), ("work_hours_per_week", "Work hours"), ("workplace_distance_km", "Workplace distance"), ("indoor_activity_distance_km", "Indoor activity distance"), ("outdoor_activity_distance_km", "Outdoor activity distance")):
                self._validate_override(key, label, n_personas)
        except ValueError as exc:
            messagebox.showerror("Invalid input", str(exc))
            return False
        return True

    def build_command(self) -> list[str]:
        """Build the command-line command for run_full_pa_simulation.py."""
        simulation_script = SIMULATION_DIR / "run_full_pa_simulation.py"
        cmd = [sys.executable, str(simulation_script)]
        mapping = {
            "n_personas": "--n-personas", "n_days": "--n-days", "start_date": "--start-date", "base_seed": "--base-seed", "output_dir": "--output-dir", "model": "--model", "temperature": "--temperature", "top_p": "--top-p", "llm1_max_tokens": "--llm1-max-tokens", "llm2_max_tokens": "--llm2-max-tokens", "state_assessment_max_tokens": "--state-assessment-max-tokens", "physical_activity_hours_per_week": "--physical-activity-hours-per-week", "social_hours_per_week": "--social-hours-per-week", "care_work_hours_per_week": "--care-work-hours-per-week", "work_hours_per_week": "--work-hours-per-week", "workplace_distance_km": "--workplace-distance-km", "indoor_activity_distance_km": "--indoor-activity-distance-km", "outdoor_activity_distance_km": "--outdoor-activity-distance-km",
        }
        for key, flag in mapping.items():
            value = str(self.vars[key].get()).strip()
            if value:
                cmd.extend([flag, value])
        llm_seed = str(self.vars["llm_seed"].get()).strip()
        if llm_seed:
            cmd.extend(["--llm-seed", llm_seed])
        if bool(self.vars["dry_run"].get()): cmd.append("--dry-run")
        cmd.append("--enable-resource-tracking" if bool(self.vars["enable_resource_tracking"].get()) else "--disable-resource-tracking")
        cmd.append("--enable-codecarbon" if bool(self.vars["enable_codecarbon"].get()) else "--disable-codecarbon")
        if bool(self.vars["verbose_llm_debug"].get()): cmd.append("--verbose-llm-debug")
        if bool(self.vars["include_full_hourly_context"].get()): cmd.append("--include-full-hourly-context")
        if bool(self.vars["state_assessment_json_mode"].get()): cmd.append("--state-assessment-json-mode")
        return cmd

    def start_simulation(self) -> None:
        if self.is_running:
            messagebox.showwarning("Simulation running", "A simulation is already running.")
            return
        if not self.validate_inputs():
            return
        if not bool(self.vars["dry_run"].get()) and not os.environ.get("UNI_LLM_API_KEY"):
            messagebox.showerror("Missing API key", f"UNI_LLM_API_KEY is missing. Add it to {ENV_PATH} or the process environment before starting a real simulation.")
            return
        cmd = self.build_command()
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
