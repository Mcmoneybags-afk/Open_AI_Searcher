import customtkinter as ctk
import sys
import threading
import io
import time
import os
import pandas as pd
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

class ArticleAdderWindow(ctk.CTkToplevel):
    def __init__(self, parent, input_folder="input_csv"):
        super().__init__(parent)
        self.title("Neuen Artikel hinzufügen")
        self.geometry("500x500")
        self.input_folder = input_folder
        
        # Fenster in den Vordergrund
        self.attributes("-topmost", True)
        self.resizable(False, False)

        # Überschrift
        self.lbl_title = ctk.CTkLabel(self, text="Artikel zur Liste hinzufügen", font=("Arial", 18, "bold"))
        self.lbl_title.pack(pady=20)

        # 1. Kategorie Auswahl (Ordner)
        self.lbl_cat = ctk.CTkLabel(self, text="Kategorie (Ordner):", anchor="w")
        self.lbl_cat.pack(fill="x", padx=40, pady=(10, 0))
        
        self.folders = self.get_subfolders()
        self.combo_cat = ctk.CTkComboBox(self, values=self.folders, width=300)
        self.combo_cat.pack(pady=5)
        if self.folders: self.combo_cat.set(self.folders[0])

        # 2. Artikelnummer
        self.entry_artnr = ctk.CTkEntry(self, placeholder_text="Artikelnummer (z.B. 106907)", width=300)
        self.entry_artnr.pack(pady=(15, 5))

        # 3. Artikelname
        self.entry_name = ctk.CTkEntry(self, placeholder_text="Artikelname (z.B. Gigabyte B860...)", width=300)
        self.entry_name.pack(pady=5)

        # 4. GTIN
        self.entry_gtin = ctk.CTkEntry(self, placeholder_text="GTIN / EAN (z.B. 471933...)", width=300)
        self.entry_gtin.pack(pady=5)

        # Speichern Button
        self.btn_save = ctk.CTkButton(self, text="💾 Speichern & Hinzufügen", command=self.save_article, fg_color="#2E8B57", hover_color="#1B5E20", height=40)
        self.btn_save.pack(pady=30)

        self.lbl_status = ctk.CTkLabel(self, text="", text_color="gray")
        self.lbl_status.pack(pady=5)

    def get_subfolders(self):
        """ Scannt den input_csv Ordner nach Unterordnern """
        if not os.path.exists(self.input_folder):
            return ["Kein Ordner gefunden"]
        
        dirs = [d for d in os.listdir(self.input_folder) if os.path.isdir(os.path.join(self.input_folder, d))]
        dirs.sort() # Alphabetisch sortieren
        return dirs

    def save_article(self):
        folder = self.combo_cat.get()
        art_nr = self.entry_artnr.get().strip()
        name = self.entry_name.get().strip()
        gtin = self.entry_gtin.get().strip()

        if not folder or not art_nr or not name:
            self.lbl_status.configure(text="⚠️ Bitte ArtNr und Name ausfüllen!", text_color="#D32F2F")
            return

        target_dir = os.path.join(self.input_folder, folder)
        
        # Suche nach Excel oder CSV Dateien im Ordner
        files = [f for f in os.listdir(target_dir) if f.lower().endswith(('.xlsx', '.xls', '.csv')) and not f.startswith("~$")]
        
        if not files:
            self.lbl_status.configure(text=f"❌ Keine Datei in {folder} gefunden!", text_color="#D32F2F")
            return
        
        # Wir nehmen einfach die erste gefundene Datei (meist artikel.xlsx)
        target_file = os.path.join(target_dir, files[0])
        ext = os.path.splitext(target_file)[1].lower()

        try:
            # 1. Datei laden
            if ext in ['.xlsx', '.xls']:
                df = pd.read_excel(target_file, dtype=str)
            else:
                df = pd.read_csv(target_file, dtype=str, sep=None, engine='python')

            # 2. Neue Zeile erstellen (als DataFrame)
            new_data = {
                "Artikelnummer": str(art_nr),
                "Artikelname": str(name),
                "GTIN": str(gtin) if gtin else ""
                # Hier könnten wir auch "Hersteller" etc. hinzufügen, wenn nötig
            }
            new_row_df = pd.DataFrame([new_data])

            # 3. Anhängen (Concat)
            df = pd.concat([df, new_row_df], ignore_index=True)

            # 4. Speichern (ohne Index)
            if ext in ['.xlsx', '.xls']:
                df.to_excel(target_file, index=False)
            else:
                df.to_csv(target_file, index=False, sep=";", encoding='utf-8')

            self.lbl_status.configure(text=f"✅ Gespeichert in: {files[0]}", text_color="#66BB6A")
            
            # Felder leeren für nächsten Eintrag
            self.entry_artnr.delete(0, 'end')
            self.entry_name.delete(0, 'end')
            self.entry_gtin.delete(0, 'end')
            self.entry_artnr.focus() # Fokus zurück auf ArtNr

        except Exception as e:
            self.lbl_status.configure(text=f"❌ Fehler: {str(e)}", text_color="#D32F2F")
            print(e)

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
        self.sidebar_frame.grid_rowconfigure(7, weight=1) # WICHTIG: Spacer ist jetzt weiter unten (Zeile 7 statt 6)

        # 1. Logo (Row 0)
        self.logo_label = ctk.CTkLabel(self.sidebar_frame, text="SYSTEMTREFF\nAI ENGINE", font=ctk.CTkFont(size=20, weight="bold"))
        self.logo_label.grid(row=0, column=0, padx=20, pady=(20, 10))

        # 2. NEU: Artikel hinzufügen (Row 1)
        self.btn_add_item = ctk.CTkButton(self.sidebar_frame, text="➕ Artikel hinzufügen", command=self.open_add_window, fg_color="#F9A825", hover_color="#FBC02D", text_color="black")
        self.btn_add_item.grid(row=1, column=0, padx=20, pady=(0, 20)) # Etwas Abstand nach unten

        # 3. Button: START (Row 2 - verschoben)
        self.btn_full_run = ctk.CTkButton(self.sidebar_frame, text="🚀 Start Komplett-Scan", command=self.start_full_run_thread)
        self.btn_full_run.grid(row=2, column=0, padx=20, pady=10)

        # 4. Button: ABBRECHEN (Row 3 - verschoben)
        self.btn_stop = ctk.CTkButton(self.sidebar_frame, text="🛑 ABBRECHEN", command=self.stop_process, fg_color="#D32F2F", hover_color="#B71C1C", state="disabled")
        self.btn_stop.grid(row=3, column=0, padx=20, pady=10)

        # Trenner 1 (Row 4)
        self.separator = ctk.CTkLabel(self.sidebar_frame, text="-"*30, text_color="gray")
        self.separator.grid(row=4, column=0, pady=5)

        # 5. Button: CSV EXPORT (Row 5)
        self.btn_csv_export = ctk.CTkButton(self.sidebar_frame, text="🐜 Nur CSV (JTL)", command=self.start_csv_export_thread, fg_color="transparent", border_width=2, text_color=("gray10", "#DCE4EE"))
        self.btn_csv_export.grid(row=5, column=0, padx=20, pady=10)

        # Trenner 2 (Row 6)
        self.separator2 = ctk.CTkLabel(self.sidebar_frame, text="-"*30, text_color="gray")
        self.separator2.grid(row=6, column=0, pady=5)

        # --- DATENBANK TOOLS (Row 7 - Container Frame) ---
        self.db_frame = ctk.CTkFrame(self.sidebar_frame, fg_color="transparent")
        self.db_frame.grid(row=7, column=0, padx=10, pady=5, sticky="ew")

        # ... (Inhalt von db_frame bleibt gleich: Entry, Single Button, Mass Button) ...
        self.lbl_db = ctk.CTkLabel(self.db_frame, text="Datenbank Upload (Live)", font=ctk.CTkFont(size=12, weight="bold"))
        self.lbl_db.pack(pady=(0,5))
        self.entry_artnr = ctk.CTkEntry(self.db_frame, placeholder_text="ArtNr (z.B. 106328)")
        self.entry_artnr.pack(fill="x", pady=(0, 5), padx=10)
        self.btn_db_single = ctk.CTkButton(self.db_frame, text="⬆️ In DB laden", command=self.start_single_db_thread, fg_color="#2E8B57", hover_color="#1B5E20")
        self.btn_db_single.pack(fill="x", padx=10)
        self.separator3 = ctk.CTkLabel(self.db_frame, text="-"*20, text_color="gray", height=10)
        self.separator3.pack(pady=2)
        self.btn_db_mass = ctk.CTkButton(self.db_frame, text="🚀 ALLES hochladen", command=self.start_mass_db_thread, fg_color="#D84315", hover_color="#BF360C")
        self.btn_db_mass.pack(fill="x", padx=10, pady=5)

        # Status Footer (Row 8)
        self.status_label = ctk.CTkLabel(self.sidebar_frame, text="Status: Bereit", text_color="gray")
        self.status_label.grid(row=8, column=0, padx=20, pady=20)

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
            
            self.btn_add_item.configure(state="disabled")
        
        else:
            # --- ALLES WIEDER FREIGEBEN ---
            self.btn_full_run.configure(state="normal")
            self.btn_csv_export.configure(state="normal")
            self.btn_db_single.configure(state="normal")
            self.btn_db_mass.configure(state="normal")    # <--- WICHTIG: Wieder freigeben
            
            # Stop-Button deaktivieren
            self.btn_stop.configure(state="disabled")
            self.status_label.configure(text="Status: Bereit / Fertig", text_color="gray")

            self.btn_add_item.configure(state="normal")

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

    def open_add_window(self):
        """ Öffnet das Fenster zum Hinzufügen """
        if self.is_running:
            messagebox.showwarning("Wartezeit", "Bitte warte, bis der aktuelle Scan beendet ist.")
            return
        
        ArticleAdderWindow(self)        

if __name__ == "__main__":
    app = SystemtreffApp()
    app.mainloop()