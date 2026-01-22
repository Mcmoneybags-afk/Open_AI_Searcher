import os
import datetime
import csv
import re
from .config import ERROR_FOLDER

# Stelle sicher, dass der Error-Ordner existiert
if not os.path.exists(ERROR_FOLDER):
    os.makedirs(ERROR_FOLDER)

CSV_LOG_FILE = os.path.join(ERROR_FOLDER, "failed_articles.csv")

def sanitize_filename(name):
    """ Entfernt Zeichen, die in Windows-Dateinamen verboten sind. """
    if not name: return "unknown_error"
    # Entferne | < > : " / \ ? *
    return re.sub(r'[\\/*?:"<>|]', "", str(name)).strip().replace(" ", "_")

def log_error(product_name, gtin, error_message, raw_content=""):
    """
    Loggt Fehler in eine CSV und speichert den rohen Antwort-Text in einer .txt Datei.
    """
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # 1. CSV Eintrag
    file_exists = os.path.isfile(CSV_LOG_FILE)
    try:
        with open(CSV_LOG_FILE, mode='a', newline='', encoding='utf-8') as f:
            writer = csv.writer(f, delimiter=';')
            if not file_exists:
                writer.writerow(["Timestamp", "Produkt", "GTIN", "Fehler", "Log-Datei"])
            
            # Dateinamen säubern!
            safe_name = sanitize_filename(product_name)
            log_filename = f"DEBUG_{safe_name}.txt"
            
            writer.writerow([timestamp, product_name, gtin, error_message, log_filename])
            print(f"   ⚠️ Fehler geloggt in: {CSV_LOG_FILE}")

        # 2. Detail-Log (Textdatei)
        if raw_content:
            debug_path = os.path.join(ERROR_FOLDER, log_filename)
            with open(debug_path, "w", encoding="utf-8") as f:
                f.write(f"PRODUKT: {product_name}\n")
                f.write(f"GTIN: {gtin}\n")
                f.write(f"FEHLER: {error_message}\n")
                f.write("-" * 40 + "\n")
                f.write("RAW RESPONSE:\n")
                f.write(raw_content)
                
    except Exception as e:
        print(f"❌ Kritisches Problem beim Loggen: {e}")