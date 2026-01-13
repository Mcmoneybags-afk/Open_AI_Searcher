import os
import csv
from datetime import datetime
from .config import ERROR_FOLDER

ERROR_CSV_PATH = os.path.join(ERROR_FOLDER, "failed_articles.csv")

def log_error(product_name, gtin, error_message, raw_content=None):
    """
    Loggt Fehler in eine zentrale CSV-Datei und speichert optional den Raw-Content.
    """
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # 1. Sicherstellen, dass der Ordner existiert
    if not os.path.exists(ERROR_FOLDER):
        os.makedirs(ERROR_FOLDER)

    # 2. Prüfen, ob CSV Header braucht (wenn Datei neu ist)
    file_exists = os.path.exists(ERROR_CSV_PATH)
    
    try:
        with open(ERROR_CSV_PATH, mode='a', newline='', encoding='utf-8') as csvfile:
            writer = csv.writer(csvfile, delimiter=';')
            
            # Header schreiben, wenn Datei neu
            if not file_exists:
                writer.writerow(['Timestamp', 'Produktname', 'GTIN', 'Fehler'])
            
            # Fehlerzeile schreiben
            writer.writerow([timestamp, product_name, gtin, str(error_message)])
            
        print(f"   ⚠️ Fehler geloggt in: {ERROR_CSV_PATH}")

        # 3. Optional: Raw Content speichern (für Debugging), falls vorhanden
        if raw_content:
            safe_name = str(product_name).replace(" ", "_").replace("/", "-")[:50]
            dump_file = os.path.join(ERROR_FOLDER, f"DEBUG_{safe_name}.txt")
            with open(dump_file, "w", encoding="utf-8") as f:
                f.write(f"Fehler: {error_message}\n")
                f.write("-" * 50 + "\n")
                f.write(raw_content)

    except Exception as e:
        print(f"❌ Kritisches Problem beim Loggen: {e}")

def clear_error_log():
    """ Löscht die alte Fehler-Log Datei beim Start (optional) """
    if os.path.exists(ERROR_CSV_PATH):
        os.remove(ERROR_CSV_PATH)