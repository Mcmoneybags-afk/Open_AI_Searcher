import os
import mysql.connector
from dotenv import load_dotenv

# .env laden
load_dotenv()

class DBConnector:
    def __init__(self, html_folder="output_HTML"):
        self.html_folder = html_folder
        self.config = {
            'user': os.getenv('DB_USER'),
            'password': os.getenv('DB_PASSWORD'),
            'host': os.getenv('DB_HOST'),
            'database': os.getenv('DB_NAME'),
            'raise_on_warnings': True
        }

    def connect(self):
        try:
            return mysql.connector.connect(**self.config)
        except mysql.connector.Error as err:
            return None, f"Verbindungsfehler: {err}"

    # --- EINZEL IMPORT ---
    def export_single_article(self, art_nr):
        """ Exportiert EINE HTML-Datei in die Datenbank. """
        filename = f"{art_nr}.html"
        file_path = os.path.join(self.html_folder, filename)
        
        if not os.path.exists(file_path):
            return False, f"❌ Datei nicht gefunden: {filename}"

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                html_content = f.read()
        except Exception as e:
            return False, f"❌ Fehler beim Lesen: {e}"

        return self._write_to_db(art_nr, html_content)

    # --- MASSEN IMPORT ---
    def export_all_articles(self, callback_log=None):
        """ 
        Exportiert ALLE HTML-Dateien aus dem Ordner.
        """
        if not os.path.exists(self.html_folder):
            return "❌ Ordner 'output_HTML' nicht gefunden!"

        files = [f for f in os.listdir(self.html_folder) if f.endswith('.html')]
        
        if not files:
            return "⚠️ Keine HTML-Dateien zum Importieren gefunden."

        if callback_log: callback_log(f"🔄 Starte Massen-Update für {len(files)} Artikel...")
        
        conn = None
        try:
            conn = mysql.connector.connect(**self.config)
            cursor = conn.cursor()
            
            success_count = 0
            skipped_count = 0
            error_count = 0
            
            for i, filename in enumerate(files):
                try:
                    art_nr = os.path.splitext(filename)[0]
                    file_path = os.path.join(self.html_folder, filename)
                    
                    with open(file_path, 'r', encoding='utf-8') as f:
                        html_content = f.read()
                    
                    # 1. Update versuchen
                    update_query = "UPDATE tartikel SET cBeschreibung = %s WHERE cArtNr = %s"
                    cursor.execute(update_query, (html_content, art_nr))
                    
                    if cursor.rowcount > 0:
                        # Fall A: Daten wurden geändert
                        success_count += 1
                        if callback_log: callback_log(f"  ✅ {art_nr}: Updated")
                    else:
                        # Fall B: Keine Änderung (0 Zeilen). Warum?
                        # Checken ob Artikel überhaupt existiert
                        cursor.execute("SELECT cArtNr FROM tartikel WHERE cArtNr = %s", (art_nr,))
                        if cursor.fetchone():
                            # Artikel da -> Daten waren identisch
                            skipped_count += 1
                            if callback_log: callback_log(f"  ℹ️ {art_nr}: Bereits aktuell (Daten identisch)")
                        else:
                            # Artikel NICHT da -> Fehler
                            error_count += 1
                            if callback_log: callback_log(f"  ⚠️ {art_nr}: Artikelnummer nicht in DB gefunden!")
                    
                    if i % 10 == 0:
                        conn.commit()

                except Exception as e:
                    error_count += 1
                    if callback_log: callback_log(f"  ❌ Fehler bei {filename}: {e}")

            conn.commit()
            cursor.close()
            return f"🏁 Fertig! Updated: {success_count} | Identisch: {skipped_count} | Nicht gefunden/Fehler: {error_count}"

        except mysql.connector.Error as err:
            return f"❌ Datenbank-Fehler: {err}"
        finally:
            if conn and conn.is_connected():
                conn.close()

    # Interne Hilfsfunktion für Einzel-Update
    def _write_to_db(self, art_nr, content):
        conn = None
        try:
            conn = mysql.connector.connect(**self.config)
            cursor = conn.cursor()
            
            # 1. Update
            update_query = "UPDATE tartikel SET cBeschreibung = %s WHERE cArtNr = %s"
            cursor.execute(update_query, (content, art_nr))
            rows = cursor.rowcount
            
            conn.commit()
            
            if rows > 0:
                msg = f"✅ Artikel '{art_nr}' erfolgreich aktualisiert."
                cursor.close()
                return True, msg
            else:
                # 2. Detail-Check: Existiert er?
                cursor.execute("SELECT cArtNr FROM tartikel WHERE cArtNr = %s", (art_nr,))
                result = cursor.fetchone()
                cursor.close()
                
                if result:
                    return True, f"ℹ️ Artikel '{art_nr}' war bereits auf dem neuesten Stand (Daten identisch)."
                else:
                    return False, f"⚠️ Artikel '{art_nr}' wurde nicht in der Datenbank gefunden!"

        except mysql.connector.Error as err:
            return False, f"SQL Fehler: {err}"
        finally:
            if conn and conn.is_connected():
                conn.close()