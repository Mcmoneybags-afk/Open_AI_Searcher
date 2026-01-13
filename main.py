import os
import re
import json
import time 
import csv
import logging
from modules.config import setup_folders, OUTPUT_FOLDER, LOG_FILE
from modules.data_handler import load_csv_optimized
from modules.prompts import get_prompt_by_category
from modules.agent import setup_agent
from modules.logger import log_error
from modules.html_generator import HTMLGenerator
from modules.image_fetcher import find_product_image
from modules.json_mapper import MarvinMapper

# --- LOGGING CONFIG ---
if os.path.exists(LOG_FILE):
    os.remove(LOG_FILE)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE, encoding='utf-8'),
        logging.StreamHandler()
    ]
)

# Name der Datei für fehlgeschlagene Artikel
RETRY_CSV_FILE = "retry_list.csv"

def check_data_quality(data):
    """
    Prüft, ob das JSON zu viele "N/A" Werte enthält.
    """
    ignored_keys = ["Kategorie", "Produktname", "Bild_URL", "_Original_GTIN", "_Produktname", "_Artikelnummer", "Besonderheiten"]
    
    total_fields = 0
    na_fields = 0
    
    for key, value in data.items():
        if key in ignored_keys:
            continue
            
        total_fields += 1
        val_str = str(value).lower().strip()
        
        if val_str in ["n/a", "na", "nein", "", "nicht verfügbar", "unknown"]:
            na_fields += 1
            
    if total_fields == 0:
        return True 
        
    failure_rate = na_fields / total_fields
    
    if failure_rate > 0.5:
        return True
        
    return False

def append_to_retry_csv(row_data):
    """ Schreibt die Zeile in die Retry-CSV (mit Semikolon ';') """
    file_exists = os.path.isfile(RETRY_CSV_FILE)
    
    with open(RETRY_CSV_FILE, mode='a', newline='', encoding='utf-8') as f:
        fieldnames = ['Artikelnummer', 'Artikelname', 'GTIN', 'EAN', 'HAN', 'Hersteller', 'Kategorie']
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction='ignore', delimiter=';')
        
        if not file_exists:
            writer.writeheader()
            
        row_dict = row_data.to_dict()
        if 'GTIN' not in row_dict and 'GTIN_Clean' in row_dict:
            row_dict['GTIN'] = row_dict['GTIN_Clean']
            
        writer.writerow(row_dict)

def main(stop_event=None):
    """ Hauptfunktion. """
    # 1. Setup
    setup_folders()
    
    # 2. Daten laden
    try:
        df_clean = load_csv_optimized()
        logging.info(f"✨ {len(df_clean)} Artikel bereit zur Verarbeitung.")
    except Exception as e:
        logging.error(f"❌ Abbruch beim Laden der CSV: {e}")
        return

    # 3. Agent starten
    agent = setup_agent()

    # 4. Loop durch die Artikel
    for index, row in df_clean.iterrows():
        
        if stop_event and stop_event.is_set():
            logging.warning("\n🛑 VORGANG VOM BENUTZER ABGEBROCHEN.")
            break

        name = row.get('Artikelname', 'Unbekannt')
        gtin = row.get('GTIN_Clean', '')
        
        # Dateinamen Logik
        art_nr = row.get('Artikelnummer', row.get('ArtNr', row.get('SKU', '')))
        
        if art_nr and str(art_nr).strip() != "":
            safe_filename = re.sub(r'[\\/*?:"<>|]', "", str(art_nr)).strip()
            safe_filename = safe_filename.replace(" ", "_")
            log_prefix = f"({index + 1}/{len(df_clean)}) ArtNr: {safe_filename}"
        else:
            safe_filename = re.sub(r'[\\/*?:"<>|]', "", str(name)).replace(" ", "_")[:80]
            log_prefix = f"({index + 1}/{len(df_clean)}) {name[:20]}..."

        json_filename = f"{safe_filename}.json"
        json_path = os.path.join(OUTPUT_FOLDER, json_filename)

        logging.info(f"🔍 {log_prefix} | Starte Suche...")

        if os.path.exists(json_path):
            print(f"⏭️  Bereits fertig.")
            continue

        prompt = get_prompt_by_category(name, gtin)

        try:
            response_text = agent.run(prompt)
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            
            if json_match:
                data = json.loads(json_match.group(0))
                
                # Bilder & Metadaten
                search_name = data.get("Produktname", name)
                category_found = data.get("Kategorie", "")
                image_url = find_product_image(search_name, category=category_found)
                data["Bild_URL"] = image_url if image_url else ""
                
                data["_Original_GTIN"] = gtin
                data["_Produktname"] = name
                data["_Artikelnummer"] = str(art_nr) 
                
                # Qualitäts-Check
                is_bad = check_data_quality(data)
                
                if is_bad:
                    logging.warning(f"⚠️  QUALITÄTS-WARNUNG: Zu viele 'N/A' Werte. Wird in {RETRY_CSV_FILE} eingetragen.")
                    append_to_retry_csv(row)
                
                with open(json_path, "w", encoding="utf-8") as f:
                    json.dump(data, f, ensure_ascii=False, indent=4)
                
                if not is_bad:
                    logging.info(f"✅ Gespeichert & Qualität OK.")
                
            else:
                log_error(name, gtin, "Kein JSON in Antwort gefunden", raw_content=response_text)
                logging.error("❌ Kein JSON gefunden. Trage in Retry-Liste ein.")
                append_to_retry_csv(row)

        except Exception as e:
            err_msg = str(e)
            logging.error(f"❌ Fehler: {err_msg}")
            log_error(name, gtin, f"Crash: {err_msg}")
            append_to_retry_csv(row)
            
            if "432" in err_msg or "quota" in err_msg.lower():
                logging.critical("\n🛑 TAVILY LIMIT ERREICHT. Stoppe Skript.")
                break 

        time.sleep(1)

    # 5. HTML & MARVIN JSON Generierung (Post-Processing)
    print("\n" + "="*50)
    logging.info("🔄 Starte Post-Processing (HTML & Marvin-Mapper)...")
    
    mapper = MarvinMapper(output_folder="output_JSON_Marvin")
    
    html_gen = None
    try:
        html_gen = HTMLGenerator(
            json_folder=OUTPUT_FOLDER, 
            output_folder="output_HTML",
            template_path="templates/template.html"
        )
    except Exception as e:
        logging.error(f"❌ Fehler beim Init HTML-Generator: {e}")

    if os.path.exists(OUTPUT_FOLDER):
        for filename in os.listdir(OUTPUT_FOLDER):
            if filename.endswith(".json"):
                file_path = os.path.join(OUTPUT_FOLDER, filename)
                
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    
                    # 1. HTML generieren
                    html_content = ""
                    if html_gen:
                        # --- HIER WAR DER FEHLER ---
                        # Wir übergeben nur 'filename' (z.B. "101312.json"), 
                        # weil der HTMLGenerator den Ordnerpfad intern selbst hinzufügt.
                        html_content = html_gen.generate_single(filename) 
                    
                    # 2. Marvin JSON erstellen
                    # Hier brauchen wir 'file_path', damit der Mapper den Dateinamen für den Output ableiten kann
                    mapper.create_json(file_path, data, html_content=html_content)
                    
                except Exception as e:
                    logging.error(f"❌ Fehler beim Post-Processing von {filename}: {e}")

    logging.info("✅ HAUPTPROGRAMM ERFOLGREICH BEENDET.")

if __name__ == "__main__":
    main()