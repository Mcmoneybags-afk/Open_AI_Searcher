import customtkinter as ctk
import sys
import threading
import io
import time
from tkinter import messagebox

# Importiere deine Module
try:
    from main import main as run_main_process
    from generate_csv_only import main as run_csv_export
except ImportError as e:
    print(f"Fehler beim Importieren der Skripte: {e}")

# --- KONFIGURATION ---
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("green")

class RedirectText(io.StringIO):
    """ Leitet print() Ausgaben in das Text-Widget um """
    def __init__(self, text_widget):
        super().__init__()
        self.text_widget = text_widget

    def write(self, string):
        try:
            self.text_widget.configure(state="normal")
            self.text_widget.insert("end", string)
            self.text_widget.see("end")
            self.text_widget.configure(state="disabled")
        except:
            pass 
        sys.__stdout__.write(string)

    def flush(self):
        sys.__stdout__.flush()

class SystemtreffApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        # Fenster Setup
        self.title("Systemtreff AI Datenblatt Generator")
        self.geometry("950x650")
        
        # Grid Layout
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # Threading Event für den Abbruch
        self.stop_event = threading.Event()
        self.is_running = False

        # --- LINKE SIDEBAR ---
        self.sidebar_frame = ctk.CTkFrame(self, width=200, corner_radius=0)
        self.sidebar_frame.grid(row=0, column=0, sticky="nsew")
        self.sidebar_frame.grid_rowconfigure(5, weight=1)

        self.logo_label = ctk.CTkLabel(self.sidebar_frame, text="SYSTEMTREFF\nAI ENGINE", font=ctk.CTkFont(size=20, weight="bold"))
        self.logo_label.grid(row=0, column=0, padx=20, pady=(20, 10))

        # Button: START
        self.btn_full_run = ctk.CTkButton(self.sidebar_frame, text="🚀 Start Komplett-Scan", command=self.start_full_run_thread)
        self.btn_full_run.grid(row=1, column=0, padx=20, pady=10)

        # Button: ABBRECHEN (Rot)
        self.btn_stop = ctk.CTkButton(self.sidebar_frame, text="🛑 ABBRECHEN", command=self.stop_process, fg_color="#D32F2F", hover_color="#B71C1C", state="disabled")
        self.btn_stop.grid(row=2, column=0, padx=20, pady=10)

        # Trenner
        self.separator = ctk.CTkLabel(self.sidebar_frame, text="-"*30, text_color="gray")
        self.separator.grid(row=3, column=0, pady=5)

        # Button: CSV EXPORT
        self.btn_csv_export = ctk.CTkButton(self.sidebar_frame, text="🐜 Nur CSV für JTL Import erstellen", command=self.start_csv_export_thread, fg_color="transparent", border_width=2, text_color=("gray10", "#DCE4EE"))
        self.btn_csv_export.grid(row=4, column=0, padx=20, pady=10)

        # Status Footer
        self.status_label = ctk.CTkLabel(self.sidebar_frame, text="Status: Bereit", text_color="gray")
        self.status_label.grid(row=6, column=0, padx=20, pady=20)

        # --- RECHTER BEREICH (Logs) ---
        self.right_frame = ctk.CTkFrame(self, corner_radius=0, fg_color="transparent")
        self.right_frame.grid(row=0, column=1, sticky="nsew", padx=20, pady=20)
        
        self.log_label = ctk.CTkLabel(self.right_frame, text="Live Prozess Protokoll:", anchor="w")
        self.log_label.pack(fill="x", pady=(0, 5))

        self.log_textbox = ctk.CTkTextbox(self.right_frame, width=600, font=("Consolas", 12))
        self.log_textbox.pack(fill="both", expand=True)
        self.log_textbox.configure(state="disabled")

        # Redirect Output
        sys.stdout = RedirectText(self.log_textbox)
        sys.stderr = RedirectText(self.log_textbox)

    def set_ui_state(self, running):
        """ Ändert Button-Zustände je nach Status """
        self.is_running = running
        if running:
            self.btn_full_run.configure(state="disabled")
            self.btn_csv_export.configure(state="disabled")
            self.btn_stop.configure(state="normal") 
            self.status_label.configure(text="Status: LÄUFT...", text_color="#66BB6A") 
        else:
            self.btn_full_run.configure(state="normal")
            self.btn_csv_export.configure(state="normal")
            self.btn_stop.configure(state="disabled")
            self.status_label.configure(text="Status: Bereit / Fertig", text_color="gray")

    def stop_process(self):
        """ Setzt das Signal zum Anhalten """
        if self.is_running:
            print("\n⚠️  ABBRUCH-SIGNAL GESENDET! Bitte warten, laufender Schritt wird beendet...")
            self.stop_event.set()
            self.btn_stop.configure(state="disabled") 

    def start_full_run_thread(self):
        if self.is_running: return
        self.stop_event.clear() 
        threading.Thread(target=self.run_full_process, daemon=True).start()

    def start_csv_export_thread(self):
        if self.is_running: return
        threading.Thread(target=self.run_csv_process, daemon=True).start()

    def run_full_process(self):
        self.set_ui_state(True)
        print("\n--- STARTE HAUPTPROGRAMM ---\n")
        try:
            run_main_process(stop_event=self.stop_event)
            
            if self.stop_event.is_set():
                print("\n⛔ PROZESS WURDE ABGEBROCHEN.")
            else:
                print("\n✅ HAUPTPROGRAMM ERFOLGREICH BEENDET.")
                
        except Exception as e:
            print(f"\n❌ KRITISCHER FEHLER: {e}")
        finally:
            self.set_ui_state(False)

    def run_csv_process(self):
        self.set_ui_state(True)
        print("\n--- STARTE CSV Erstellung ---\n")
        try:
            run_csv_export()
            print("\n✅ EXPORT BEENDET.")
        except Exception as e:
            print(f"\n❌ FEHLER: {e}")
        finally:
            self.set_ui_state(False)

if __name__ == "__main__":
    app = SystemtreffApp()
    app.mainloop()