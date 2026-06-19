#!/usr/bin/env python3
"""
GUI für die PA-Simulation (run_full_pa_simulation.py)
Ermöglicht benutzerfreundliche Konfiguration aller Parameter
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from datetime import date, timedelta
from pathlib import Path
import subprocess
import sys
import threading
from typing import Optional, Dict, Any

# Standardwerte aus run_full_pa_simulation.py
SIMULATION_DIR = Path(__file__).resolve().parent
DEFAULT_OUTPUT_DIR = SIMULATION_DIR / "output" / "full_pa_simulation"
DEFAULT_MODEL = "gpt-oss-120b"
DEFAULT_TEMPERATURE = 0
DEFAULT_TOP_P = 1.0
DEFAULT_LLM1_MAX_TOKENS = 10000
DEFAULT_LLM2_MAX_TOKENS = 10000
DEFAULT_STATE_ASSESSMENT_MAX_TOKENS = 10000


class PASimulationGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("PA-Simulation Konfiguration")
        self.root.geometry("900x1100")
        self.root.configure(bg="#e8edf3")
        
        self.process = None
        self.is_running = False
        
        # Erstelle Main Frame mit Scrollbar
        self.create_ui()
        
    def create_ui(self):
        """Erstelle die Benutzeroberfläche"""
        self.style = ttk.Style(self.root)
        try:
            self.style.theme_use("clam")
        except tk.TclError:
            pass
        self.style.configure("Header.TLabel", font=("Segoe UI", 13, "bold"), background="#e8edf3")
        self.style.configure("TLabel", font=("Segoe UI", 10), background="#e8edf3")
        self.style.configure("TEntry", padding=4)
        self.style.configure("TButton", padding=(8, 5))
        self.style.configure("TLabelframe", background="#f7f9fc", borderwidth=1)
        self.style.configure("TLabelframe.Label", font=("Segoe UI", 11, "bold"))
        self.style.configure("TFrame", background="#e8edf3")
        # Main Frame mit Scrollbar
        main_frame = ttk.Frame(self.root, style="TFrame")
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Canvas für Scrolling
        canvas = tk.Canvas(main_frame, highlightthickness=0)
        scrollbar = ttk.Scrollbar(main_frame, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        header_label = ttk.Label(scrollable_frame, text="PA-Simulation Konfiguration", style="Header.TLabel")
        header_label.pack(anchor=tk.W, pady=(0, 10))

        # ===== GRUNDPARAMETER =====
        basic_frame = ttk.LabelFrame(scrollable_frame, text="Grundparameter", padding=10)
        basic_frame.pack(fill=tk.X, pady=5)
        basic_frame.columnconfigure(1, weight=1)
        
        # Anzahl Personas
        ttk.Label(basic_frame, text="Anzahl Personas:").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.n_personas = tk.StringVar(value="2")
        ttk.Spinbox(basic_frame, from_=1, to=100, textvariable=self.n_personas, width=10).grid(row=0, column=1, sticky=tk.W)
        
        # Anzahl Tage
        ttk.Label(basic_frame, text="Anzahl Tage:").grid(row=1, column=0, sticky=tk.W, pady=5)
        self.n_days = tk.StringVar(value="2")
        ttk.Spinbox(basic_frame, from_=1, to=365, textvariable=self.n_days, width=10).grid(row=1, column=1, sticky=tk.W)
        
        # Startdatum
        ttk.Label(basic_frame, text="Startdatum:").grid(row=2, column=0, sticky=tk.W, pady=5)
        self.start_date = tk.StringVar(value="2026-01-01")
        ttk.Entry(basic_frame, textvariable=self.start_date, width=20).grid(row=2, column=1, sticky=tk.W)
        ttk.Label(basic_frame, text="(YYYY-MM-DD)", font=("TkDefaultFont", 8)).grid(row=2, column=2, sticky=tk.W)
        
        # Basis-Seed
        ttk.Label(basic_frame, text="Basis Seed:").grid(row=3, column=0, sticky=tk.W, pady=5)
        self.base_seed = tk.StringVar(value="137")
        ttk.Spinbox(basic_frame, from_=0, to=999999, textvariable=self.base_seed, width=10).grid(row=3, column=1, sticky=tk.W)
        
        # ===== LLM PARAMETER =====
        llm_frame = ttk.LabelFrame(scrollable_frame, text="LLM Parameter", padding=10)
        llm_frame.pack(fill=tk.X, pady=5)
        
        # Modell
        ttk.Label(llm_frame, text="Modell:").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.model = tk.StringVar(value=DEFAULT_MODEL)
        model_combo = ttk.Combobox(llm_frame, textvariable=self.model, width=25, state="normal")
        model_combo['values'] = ("gpt-oss-120b")
        model_combo.grid(state="readonly")
        
        # Temperature
        validate_float = self.root.register(self.validate_float)
        ttk.Label(llm_frame, text="Temperature:").grid(row=1, column=0, sticky=tk.W, pady=5)
        self.temperature = tk.StringVar(value=str(DEFAULT_TEMPERATURE))
        ttk.Entry(llm_frame, textvariable=self.temperature, width=12, validate="key", validatecommand=(validate_float, "%P")).grid(row=1, column=1, sticky=tk.W)
        ttk.Label(llm_frame, text="(0.0-2.0)", font=("TkDefaultFont", 8)).grid(row=1, column=2, sticky=tk.W)
        
        # Top P
        ttk.Label(llm_frame, text="Top P:").grid(row=2, column=0, sticky=tk.W, pady=5)
        self.top_p = tk.StringVar(value=str(DEFAULT_TOP_P))
        ttk.Entry(llm_frame, textvariable=self.top_p, width=12, validate="key", validatecommand=(validate_float, "%P")).grid(row=2, column=1, sticky=tk.W)
        ttk.Label(llm_frame, text="(0.0-1.0)", font=("TkDefaultFont", 8)).grid(row=2, column=2, sticky=tk.W)
        
        # LLM Seed
        ttk.Label(llm_frame, text="LLM Seed (optional):").grid(row=3, column=0, sticky=tk.W, pady=5)
        self.llm_seed = tk.StringVar(value="")
        ttk.Spinbox(llm_frame, from_=0, to=999999, textvariable=self.llm_seed, width=10).grid(row=3, column=1, sticky=tk.W)
        
        # LLM1 Max Tokens
        ttk.Label(llm_frame, text="LLM1 Max Tokens:").grid(row=4, column=0, sticky=tk.W, pady=5)
        self.llm1_max_tokens = tk.StringVar(value=str(DEFAULT_LLM1_MAX_TOKENS))
        ttk.Spinbox(llm_frame, from_=100, to=10000, textvariable=self.llm1_max_tokens, width=10).grid(row=4, column=1, sticky=tk.W)
        
        # LLM2 Max Tokens
        ttk.Label(llm_frame, text="LLM2 Max Tokens:").grid(row=5, column=0, sticky=tk.W, pady=5)
        self.llm2_max_tokens = tk.StringVar(value=str(DEFAULT_LLM2_MAX_TOKENS))
        ttk.Spinbox(llm_frame, from_=100, to=10000, textvariable=self.llm2_max_tokens, width=10).grid(row=5, column=1, sticky=tk.W)
        
        # State Assessment Max Tokens
        ttk.Label(llm_frame, text="State Assessment Max Tokens:").grid(row=6, column=0, sticky=tk.W, pady=5)
        self.state_assessment_max_tokens = tk.StringVar(value=str(DEFAULT_STATE_ASSESSMENT_MAX_TOKENS))
        ttk.Spinbox(llm_frame, from_=100, to=10000, textvariable=self.state_assessment_max_tokens, width=10).grid(row=6, column=1, sticky=tk.W)
        
        # ===== VERHALTEN PARAMETER =====
        behavior_frame = ttk.LabelFrame(scrollable_frame, text="Verhaltsparameter", padding=10)
        behavior_frame.pack(fill=tk.X, pady=5)
        behavior_frame.columnconfigure(1, weight=1)
        
        # Physical Activity Hours per Week
        ttk.Label(behavior_frame, text="PA Stunden pro Woche (optional):").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.pa_hours = tk.StringVar(value="")
        ttk.Entry(behavior_frame, textvariable=self.pa_hours, width=30).grid(row=0, column=1, sticky=tk.W)
        ttk.Label(behavior_frame, text="(Zahl oder komma-getrennte Liste)", font=("TkDefaultFont", 8)).grid(row=0, column=2, sticky=tk.W)
        
        # Social Hours per Week
        ttk.Label(behavior_frame, text="Soziale Stunden pro Woche (optional):").grid(row=1, column=0, sticky=tk.W, pady=5)
        self.social_hours = tk.StringVar(value="")
        ttk.Entry(behavior_frame, textvariable=self.social_hours, width=30).grid(row=1, column=1, sticky=tk.W)
        ttk.Label(behavior_frame, text="(Zahl oder komma-getrennte Liste)", font=("TkDefaultFont", 8)).grid(row=1, column=2, sticky=tk.W)
        
        # Care Work Hours per Week
        ttk.Label(behavior_frame, text="Caregiving Stunden pro Woche (optional):").grid(row=2, column=0, sticky=tk.W, pady=5)
        self.carework_hours = tk.StringVar(value="")
        ttk.Entry(behavior_frame, textvariable=self.carework_hours, width=30).grid(row=2, column=1, sticky=tk.W)
        ttk.Label(behavior_frame, text="(Zahl oder komma-getrennte Liste)", font=("TkDefaultFont", 8)).grid(row=2, column=2, sticky=tk.W)
        
        # Work Hours per Week
        ttk.Label(behavior_frame, text="Arbeitsstunden pro Woche (optional):").grid(row=3, column=0, sticky=tk.W, pady=5)
        self.work_hours = tk.StringVar(value="")
        ttk.Entry(behavior_frame, textvariable=self.work_hours, width=30).grid(row=3, column=1, sticky=tk.W)
        ttk.Label(behavior_frame, text="(Zahl oder komma-getrennte Liste)", font=("TkDefaultFont", 8)).grid(row=3, column=2, sticky=tk.W)
        
        # ===== ENTFERNUNGSPARAMETER (POI) =====
        poi_frame = ttk.LabelFrame(scrollable_frame, text="POI Entfernungen (optional, in km)", padding=10)
        poi_frame.pack(fill=tk.X, pady=5)
        
        poi_frame.columnconfigure(1, weight=1)
        # Workplace Distance
        ttk.Label(poi_frame, text="Arbeitsplatz Entfernung:").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.workplace_distance = tk.StringVar(value="")
        ttk.Entry(poi_frame, textvariable=self.workplace_distance, width=30).grid(row=0, column=1, sticky=tk.W)
        ttk.Label(poi_frame, text="(km als Zahl, Dezimalpunkt möglich)", font=("TkDefaultFont", 8)).grid(row=0, column=2, sticky=tk.W)
        
        # Indoor Activity Distance
        ttk.Label(poi_frame, text="Indoor Aktivität Entfernung:").grid(row=1, column=0, sticky=tk.W, pady=5)
        self.indoor_distance = tk.StringVar(value="")
        ttk.Entry(poi_frame, textvariable=self.indoor_distance, width=30).grid(row=1, column=1, sticky=tk.W)
        ttk.Label(poi_frame, text="(km als Zahl, Dezimalpunkt möglich)", font=("TkDefaultFont", 8)).grid(row=1, column=2, sticky=tk.W)
        
        # Outdoor Activity Distance
        ttk.Label(poi_frame, text="Outdoor Aktivität Entfernung:").grid(row=2, column=0, sticky=tk.W, pady=5)
        self.outdoor_distance = tk.StringVar(value="")
        ttk.Entry(poi_frame, textvariable=self.outdoor_distance, width=30).grid(row=2, column=1, sticky=tk.W)
        ttk.Label(poi_frame, text="(km als Zahl, Dezimalpunkt möglich)", font=("TkDefaultFont", 8)).grid(row=2, column=2, sticky=tk.W)
        
        # ===== OPTIONEN =====
        options_frame = ttk.LabelFrame(scrollable_frame, text="Optionen", padding=10)
        options_frame.pack(fill=tk.X, pady=5)
        
        # Dry Run
        self.dry_run = tk.BooleanVar(value=False)
        ttk.Checkbutton(options_frame, text="Dry Run Mode", variable=self.dry_run).grid(row=0, column=0, sticky=tk.W, pady=5)
        
        # Enable Resource Tracking
        self.resource_tracking = tk.BooleanVar(value=True)
        ttk.Checkbutton(options_frame, text="Resource Tracking aktivieren", variable=self.resource_tracking).grid(row=1, column=0, sticky=tk.W, pady=5)
        
        # Enable CodeCarbon
        self.codecarbon = tk.BooleanVar(value=True)
        ttk.Checkbutton(options_frame, text="CodeCarbon Tracking aktivieren", variable=self.codecarbon).grid(row=2, column=0, sticky=tk.W, pady=5)
        
        # Verbose LLM Debug
        self.verbose_debug = tk.BooleanVar(value=False)
        ttk.Checkbutton(options_frame, text="Verbose LLM Debug aktivieren", variable=self.verbose_debug).grid(row=3, column=0, sticky=tk.W, pady=5)
        
        # Include Full Hourly Context
        self.full_hourly_context = tk.BooleanVar(value=False)
        ttk.Checkbutton(options_frame, text="Include Full Hourly Context", variable=self.full_hourly_context).grid(row=4, column=0, sticky=tk.W, pady=5)
        
        # State Assessment JSON Mode
        self.json_mode = tk.BooleanVar(value=False)
        ttk.Checkbutton(options_frame, text="State Assessment JSON Mode", variable=self.json_mode).grid(row=5, column=0, sticky=tk.W, pady=5)
        
        # ===== OUTPUT VERZEICHNIS =====
        output_frame = ttk.LabelFrame(scrollable_frame, text="Output Verzeichnis", padding=10)
        output_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(output_frame, text="Output Pfad:").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.output_dir = tk.StringVar(value=str(DEFAULT_OUTPUT_DIR))
        output_entry = ttk.Entry(output_frame, textvariable=self.output_dir, width=60)
        output_entry.grid(row=0, column=1, sticky=tk.EW, padx=5)
        ttk.Button(output_frame, text="Durchsuchen...", command=self.browse_output_dir).grid(row=0, column=2, padx=5)
        output_frame.columnconfigure(1, weight=1)
        
        # ===== AKTIONSBUTTONS =====
        action_frame = ttk.Frame(scrollable_frame)
        action_frame.pack(fill=tk.X, pady=20)
        
        ttk.Button(action_frame, text="▶ Simulation starten", command=self.run_simulation).pack(side=tk.LEFT, padx=5)
        ttk.Button(action_frame, text="Stoppen", command=self.stop_simulation).pack(side=tk.LEFT, padx=5)
        ttk.Button(action_frame, text="Output Ordner öffnen", command=self.open_output_dir).pack(side=tk.LEFT, padx=5)
        ttk.Button(action_frame, text="Standardwerte zurücksetzen", command=self.reset_to_defaults).pack(side=tk.LEFT, padx=5)
        
        # ===== OUTPUT TEXT =====
        output_frame2 = ttk.LabelFrame(scrollable_frame, text="Ausgabe", padding=10)
        output_frame2.pack(fill=tk.BOTH, expand=True, pady=5)
        
        self.output_text = tk.Text(output_frame2, height=10, width=80, state=tk.DISABLED)
        scrollbar_text = ttk.Scrollbar(output_frame2, orient="vertical", command=self.output_text.yview)
        self.output_text.config(yscrollcommand=scrollbar_text.set)
        
        self.output_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar_text.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Pack Canvas und Scrollbar
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
    def validate_float(self, value: str) -> bool:
        """Validiert Eingaben für numerische Fließkommazahlen."""
        if value == "":
            return True
        try:
            float(value)
            return True
        except ValueError:
            return False

    def browse_output_dir(self):
        """Öffnet Dialog zum Auswählen des Output-Verzeichnisses"""
        directory = filedialog.askdirectory(
            title="Output Verzeichnis auswählen",
            initialdir=str(self.output_dir.get())
        )
        if directory:
            self.output_dir.set(directory)
    
    def open_output_dir(self):
        """Öffnet das Output-Verzeichnis im Explorer"""
        output_path = Path(self.output_dir.get())
        output_path.mkdir(parents=True, exist_ok=True)
        
        import os
        import platform
        
        try:
            if platform.system() == "Windows":
                os.startfile(output_path)
            elif platform.system() == "Darwin":
                subprocess.Popen(["open", str(output_path)])
            else:
                subprocess.Popen(["xdg-open", str(output_path)])
        except Exception as e:
            messagebox.showerror("Fehler", f"Konnte Verzeichnis nicht öffnen: {e}")
    
    def log_output(self, message: str):
        """Fügt Nachricht zum Output-Text hinzu"""
        self.output_text.config(state=tk.NORMAL)
        self.output_text.insert(tk.END, message + "\n")
        self.output_text.see(tk.END)
        self.output_text.config(state=tk.DISABLED)
        self.root.update()
    
    def build_command(self) -> list[str]:
        """Erstellt das Kommandozeilenbefehle"""
        cmd = [
            sys.executable, "-m", "Simulation.run_full_pa_simulation",
            "--n-personas", self.n_personas.get(),
            "--n-days", self.n_days.get(),
            "--start-date", self.start_date.get(),
            "--base-seed", self.base_seed.get(),
            "--model", self.model.get(),
            "--temperature", self.temperature.get(),
            "--top-p", self.top_p.get(),
            "--llm1-max-tokens", self.llm1_max_tokens.get(),
            "--llm2-max-tokens", self.llm2_max_tokens.get(),
            "--state-assessment-max-tokens", self.state_assessment_max_tokens.get(),
            "--output-dir", self.output_dir.get(),
        ]
        
        # Optional LLM Seed
        if self.llm_seed.get().strip():
            cmd.extend(["--llm-seed", self.llm_seed.get()])
        
        # Optional Behavior Parameters
        if self.pa_hours.get().strip():
            cmd.extend(["--physical-activity-hours-per-week", self.pa_hours.get()])
        if self.social_hours.get().strip():
            cmd.extend(["--social-hours-per-week", self.social_hours.get()])
        if self.carework_hours.get().strip():
            cmd.extend(["--care-work-hours-per-week", self.carework_hours.get()])
        if self.work_hours.get().strip():
            cmd.extend(["--work-hours-per-week", self.work_hours.get()])
        
        # Optional POI Distances
        if self.workplace_distance.get().strip():
            cmd.extend(["--workplace-distance-km", self.workplace_distance.get()])
        if self.indoor_distance.get().strip():
            cmd.extend(["--indoor-activity-distance-km", self.indoor_distance.get()])
        if self.outdoor_distance.get().strip():
            cmd.extend(["--outdoor-activity-distance-km", self.outdoor_distance.get()])
        
        # Flags
        if self.dry_run.get():
            cmd.append("--dry-run")
        if self.resource_tracking.get():
            cmd.append("--enable-resource-tracking")
        else:
            cmd.append("--disable-resource-tracking")
        if self.codecarbon.get():
            cmd.append("--enable-codecarbon")
        else:
            cmd.append("--disable-codecarbon")
        if self.verbose_debug.get():
            cmd.append("--verbose-llm-debug")
        if self.full_hourly_context.get():
            cmd.append("--include-full-hourly-context")
        if self.json_mode.get():
            cmd.append("--state-assessment-json-mode")
        
        return cmd
    
    def run_simulation(self):
        """Führt die Simulation in einem separaten Thread aus"""
        if self.is_running:
            messagebox.showwarning("Warnung", "Simulation läuft bereits!")
            return
        
        # Validierung
        try:
            int(self.n_personas.get())
            int(self.n_days.get())
            int(self.base_seed.get())
            float(self.temperature.get())
            float(self.top_p.get())
            date.fromisoformat(self.start_date.get())
        except ValueError as e:
            messagebox.showerror("Eingabefehler", f"Ungültige Eingabe: {e}")
            return
        
        self.is_running = True
        self.log_output("=" * 80)
        self.log_output("Starte Simulation...")
        self.log_output(f"Startzeit: {date.today()}")
        self.log_output("=" * 80)
        
        cmd = self.build_command()
        self.log_output(f"\nBefehl: {' '.join(cmd)}\n")
        
        # Starten Sie in einem separaten Thread
        thread = threading.Thread(target=self._run_simulation_thread, args=(cmd,), daemon=True)
        thread.start()
    
    def _run_simulation_thread(self, cmd: list[str]):
        """Führt die Simulation in einem Thread aus"""
        try:
            # Wechsel zum Hauptverzeichnis
            import os
            os.chdir(SIMULATION_DIR.parent)
            
            self.process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                universal_newlines=True,
                bufsize=1
            )
            
            # Lese Output zeilenweise
            if self.process.stdout:
                for line in self.process.stdout:
                    self.log_output(line.rstrip())
            
            self.process.wait()
            
            self.log_output("\n" + "=" * 80)
            if self.process.returncode == 0:
                self.log_output("✓ Simulation erfolgreich abgeschlossen!")
            else:
                self.log_output(f"✗ Simulation mit Exit-Code {self.process.returncode} beendet")
            self.log_output("=" * 80)
            
        except Exception as e:
            self.log_output(f"\n✗ Fehler: {e}")
        finally:
            self.is_running = False
            self.process = None
    
    def stop_simulation(self):
        """Stoppt die laufende Simulation"""
        if self.process is None:
            messagebox.showinfo("Info", "Keine laufende Simulation")
            return
        
        try:
            import signal
            import os
            
            # Killt den Prozess
            if os.name == 'nt':  # Windows
                self.process.terminate()
            else:  # Unix/Linux/Mac
                os.kill(self.process.pid, signal.SIGTERM)
            
            self.log_output("\n✗ Simulation wurde beendet")
            self.is_running = False
        except Exception as e:
            self.log_output(f"\n✗ Fehler beim Stoppen: {e}")
    
    def reset_to_defaults(self):
        """Setzt alle Werte auf Standardwerte zurück"""
        self.n_personas.set("2")
        self.n_days.set("2")
        self.start_date.set("2026-01-01")
        self.base_seed.set("137")
        self.model.set(DEFAULT_MODEL)
        self.temperature.set(str(DEFAULT_TEMPERATURE))
        self.top_p.set(str(DEFAULT_TOP_P))
        self.llm_seed.set("")
        self.llm1_max_tokens.set(str(DEFAULT_LLM1_MAX_TOKENS))
        self.llm2_max_tokens.set(str(DEFAULT_LLM2_MAX_TOKENS))
        self.state_assessment_max_tokens.set(str(DEFAULT_STATE_ASSESSMENT_MAX_TOKENS))
        self.pa_hours.set("")
        self.social_hours.set("")
        self.carework_hours.set("")
        self.work_hours.set("")
        self.workplace_distance.set("")
        self.indoor_distance.set("")
        self.outdoor_distance.set("")
        self.dry_run.set(False)
        self.resource_tracking.set(True)
        self.codecarbon.set(True)
        self.verbose_debug.set(False)
        self.full_hourly_context.set(False)
        self.json_mode.set(False)
        self.output_dir.set(str(DEFAULT_OUTPUT_DIR))
        self.output_text.config(state=tk.NORMAL)
        self.output_text.delete(1.0, tk.END)
        self.output_text.config(state=tk.DISABLED)


def main():
    root = tk.Tk()
    app = PASimulationGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
