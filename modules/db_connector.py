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

    def export_single_article(self, art_nr):
        """
        Exportiert EINE HTML-Datei in die Datenbank.
        Rückgabe: (Success: bool, Message: str)
        """
        # 1. Prüfen: Gibt es die HTML-Datei?
        filename = f"{art_nr}.html"
        file_path = os.path.join(self.html_folder, filename)
        
        if not os.path.exists(file_path):
            return False, f"❌ Datei nicht gefunden: {filename} (Bitte erst generieren!)"

        # 2. HTML lesen
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                html_content = f.read()
        except Exception as e:
            return False, f"❌ Fehler beim Lesen der Datei: {e}"

        # 3. Datenbank Update
        conn = None
        try:
            conn = mysql.connector.connect(**self.config)
            cursor = conn.cursor()
            
            # Prüfen ob Artikel existiert
            check_query = "SELECT cName FROM tartikel WHERE cArtNr = %s"
            cursor.execute(check_query, (art_nr,))
            result = cursor.fetchone()
            
            if not result:
                return False, f"⚠️ Artikelnummer '{art_nr}' nicht in DB gefunden!"
            
            # UPDATE ausführen
            update_query = "UPDATE tartikel SET cBeschreibung = %s WHERE cArtNr = %s"
            cursor.execute(update_query, (html_content, art_nr))
            conn.commit()
            
            rows = cursor.rowcount
            cursor.close()
            conn.close()
            
            if rows > 0:
                return True, f"✅ Erfolgreich! Artikel '{result[0]}' aktualisiert."
            else:
                return True, f"⚠️ Update lief durch, aber keine Änderung (Text war identisch?)."

        except mysql.connector.Error as err:
            return False, f"❌ SQL Fehler: {err}"
        finally:
            if conn and conn.is_connected():
                conn.close()