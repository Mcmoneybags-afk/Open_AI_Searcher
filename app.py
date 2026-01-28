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
    # NEU: Datenbank Connector importieren
    from modules.db_connector import DBConnector
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
        self.geometry("1100x700") # Etwas breiter gemacht für die neuen Tools
        
        # Grid Layout
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # Threading Event für den Abbruch
        self.stop_event = threading.Event()
        self.is_running = False

        # --- LINKE SIDEBAR ---
        self.sidebar_frame = ctk.CTkFrame(self, width=250, corner_radius=0)
        self.sidebar_frame.grid(row=0, column=0, sticky="nsew")
        self.sidebar_frame.grid_rowconfigure(6, weight=1) # Spacer verschoben

        # Logo
        self.logo_label = ctk.CTkLabel(self.sidebar_frame, text="SYSTEMTREFF\nAI ENGINE", font=ctk.CTkFont(size=20, weight="bold"))
        self.logo_label.grid(row=0, column=0, padx=20, pady=(20, 10))

        # Button: START
        self.btn_full_run = ctk.CTkButton(self.sidebar_frame, text="🚀 Start Komplett-Scan", command=self.start_full_run_thread)
        self.btn_full_run.grid(row=1, column=0, padx=20, pady=10)

        # Button: ABBRECHEN (Rot)
        self.btn_stop = ctk.CTkButton(self.sidebar_frame, text="🛑 ABBRECHEN", command=self.stop_process, fg_color="#D32F2F", hover_color="#B71C1C", state="disabled")
        self.btn_stop.grid(row=2, column=0, padx=20, pady=10)

        # Trenner 1
        self.separator = ctk.CTkLabel(self.sidebar_frame, text="-"*30, text_color="gray")
        self.separator.grid(row=3, column=0, pady=5)

        # Button: CSV EXPORT
        self.btn_csv_export = ctk.CTkButton(self.sidebar_frame, text="🐜 Nur CSV (JTL)", command=self.start_csv_export_thread, fg_color="transparent", border_width=2, text_color=("gray10", "#DCE4EE"))
        self.btn_csv_export.grid(row=4, column=0, padx=20, pady=10)

        # Trenner 2 (für DB Bereich)
        self.separator2 = ctk.CTkLabel(self.sidebar_frame, text="-"*30, text_color="gray")
        self.separator2.grid(row=5, column=0, pady=5)

        # --- NEU: DATENBANK TOOLS ---
        self.db_frame = ctk.CTkFrame(self.sidebar_frame, fg_color="transparent")
        self.db_frame.grid(row=6, column=0, padx=10, pady=5, sticky="ew")

        self.lbl_db = ctk.CTkLabel(self.db_frame, text="Datenbank Upload (Live)", font=ctk.CTkFont(size=12, weight="bold"))
        self.lbl_db.pack(pady=(0,5))

        self.entry_artnr = ctk.CTkEntry(self.db_frame, placeholder_text="ArtNr (z.B. 106328)")
        self.entry_artnr.pack(fill="x", pady=(0, 5), padx=10)

        self.btn_db_single = ctk.CTkButton(self.db_frame, text="⬆️ In DB laden", command=self.start_single_db_thread, fg_color="#2E8B57", hover_color="#1B5E20")
        self.btn_db_single.pack(fill="x", padx=10)

        # Trennlinie
        self.separator3 = ctk.CTkLabel(self.db_frame, text="-"*20, text_color="gray", height=10)
        self.separator3.pack(pady=2)

        # MASSEN BUTTON
        self.btn_db_mass = ctk.CTkButton(self.db_frame, text="🚀 ALLES hochladen", command=self.start_mass_db_thread, fg_color="#D84315", hover_color="#BF360C")
        self.btn_db_mass.pack(fill="x", padx=10, pady=5)

        # Status Footer
        self.status_label = ctk.CTkLabel(self.sidebar_frame, text="Status: Bereit", text_color="gray")
        self.status_label.grid(row=7, column=0, padx=20, pady=20)

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
            # --- ALLES SPERREN ---
            self.btn_full_run.configure(state="disabled")
            self.btn_csv_export.configure(state="disabled")
            self.btn_db_single.configure(state="disabled")
            self.btn_db_mass.configure(state="disabled")  # <--- WICHTIG: Auch diesen Button sperren!
            
            # Stop-Button aktivieren
            self.btn_stop.configure(state="normal") 
            self.status_label.configure(text="Status: LÄUFT...", text_color="#66BB6A") 
        
        else:
            # --- ALLES WIEDER FREIGEBEN ---
            self.btn_full_run.configure(state="normal")
            self.btn_csv_export.configure(state="normal")
            self.btn_db_single.configure(state="normal")
            self.btn_db_mass.configure(state="normal")    # <--- WICHTIG: Wieder freigeben
            
            # Stop-Button deaktivieren
            self.btn_stop.configure(state="disabled")
            self.status_label.configure(text="Status: Bereit / Fertig", text_color="gray")

    def stop_process(self):
        if self.is_running:
            print("\n⚠️  ABBRUCH-SIGNAL GESENDET! Bitte warten...")
            self.stop_event.set()
            self.btn_stop.configure(state="disabled") 

    def start_full_run_thread(self):
        if self.is_running: return
        self.stop_event.clear() 
        threading.Thread(target=self.run_full_process, daemon=True).start()

    def start_csv_export_thread(self):
        if self.is_running: return
        threading.Thread(target=self.run_csv_process, daemon=True).start()

    # --- NEU: DB Thread Start ---
    def start_single_db_thread(self):
        if self.is_running: return
        art_nr = self.entry_artnr.get().strip()
        
        if not art_nr:
            messagebox.showwarning("Fehler", "Bitte eine Artikelnummer eingeben!")
            return

        # Sicherheitsabfrage
        if not messagebox.askyesno("Datenbank Update", f"Soll der Artikel '{art_nr}' wirklich in der LIVE-DB überschrieben werden?"):
            return

        threading.Thread(target=self.run_single_db_upload, args=(art_nr,), daemon=True).start()

    # --- MASSEN UPLOAD LOGIK ---
    def start_mass_db_thread(self):
        if self.is_running: return
        
        # Sicherheitsabfrage (WICHTIG!)
        confirm = messagebox.askyesno(
            "ACHTUNG: Massen-Upload", 
            "Möchtest du wirklich ALLE HTML-Dateien aus dem Ordner in die LIVE-Datenbank schreiben?\n\n"
            "⚠️ Bestehende Beschreibungen werden unwiderruflich überschrieben!\n"
            "Hast du ein Backup gemacht?"
        )
        
        if confirm:
            threading.Thread(target=self.run_mass_db_upload, daemon=True).start()

    def run_mass_db_upload(self):
        self.set_ui_state(True)
        print("\n--- 🚀 STARTE MASSEN-DB-UPLOAD ---\n")
        
        try:
            connector = DBConnector()
            # Wir geben 'print' mit, damit das Skript direkt ins Textfeld schreibt
            final_msg = connector.export_all_articles(callback_log=print)
            
            print("\n" + final_msg)
            messagebox.showinfo("Abschluss", final_msg)
            
        except Exception as e:
            print(f"\n❌ FEHLER: {e}")
            messagebox.showerror("Kritischer Fehler", str(e))
        finally:
            self.set_ui_state(False)    

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

    # --- NEU: DB Upload Logik ---
    def run_single_db_upload(self, art_nr):
        self.set_ui_state(True)
        print(f"\n--- Starte DB-Upload für {art_nr} ---\n")
        try:
            connector = DBConnector() # Benutzt Standardordner "output_HTML"
            success, msg = connector.export_single_article(art_nr)
            
            if success:
                print(msg)
                messagebox.showinfo("Erfolg", msg)
            else:
                print(msg)
                messagebox.showerror("Fehler", msg)
                
        except Exception as e:
            print(f"\n❌ UNERWARTETER FEHLER: {e}")
        finally:
            self.set_ui_state(False)

if __name__ == "__main__":
    app = SystemtreffApp()
    app.mainloop()