import os
import re
import json
import time 
import csv
import logging
import pandas as pd
from modules.config import setup_folders, OUTPUT_FOLDER, LOG_FILE
from modules.prompts import get_prompt_by_category
from modules.agent import setup_agent
from modules.logger import log_error
from modules.html_generator import HTMLGenerator
from modules.image_fetcher import find_product_image
from modules.json_mapper import MarvinMapper

# --- LOGGING CONFIG ---
if os.path.exists(LOG_FILE):
    try: os.remove(LOG_FILE)
    except: pass

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE, encoding='utf-8'),
        logging.StreamHandler()
    ]
)

RETRY_CSV_FILE = "retry_list.csv"
INPUT_FOLDER = "input_csv"

# ==============================================================================
# 📂 FOLDER MAPPING
# ==============================================================================
FOLDER_MAPPING = {
    "02_Arbeitsspeicher": "Arbeitsspeicher",
    "03_Gehaeuse": "Gehäuse",
    "04_Grafikkarten": "Grafikkarte",
    "05_Mainboards": "Mainboard",
    "06_Netzteile": "Netzteil",
    "07_Prozessor_AMD": "Prozessor",
    "08_Prozessor_Intel": "Prozessor",
    "09_CPU_Kuehler": "CPU-Kühler",
    "10_TFTs": "Monitor",
    "10_Monitore": "Monitor",
    "11_Gehaeuseluefter": "Gehäuselüfter",
    "12_Kuehler": "Kühler",
    "13_Speichermedien": "Speicher",
    "13_Speicher": "Speicher",
    "14_Eingabegeraete": "Eingabegeräte",
    "15_Kabel_Adapter": "Kabel",
    "16_Soundkarten": "Soundkarte",
    "35_Maeuse": "Eingabegeräte", 
    "34_Tastaturen": "Eingabegeräte",
    
}

def read_csv_robust(filepath):
    """
    Versucht verschiedene Encodings (UTF-8, Latin-1) und filtert leere Zeilen.
    """
    encodings = ['utf-8', 'latin-1', 'cp1252']
    
    for enc in encodings:
        try:
            # dtype=str sorgt dafür, dass "00123" nicht zu 123 wird
            df = pd.read_csv(filepath, sep=None, engine='python', dtype=str, encoding=enc).fillna('')
            
            # 🧹 CLEANING: Leere Zeilen entfernen
            # Wir prüfen, ob 'Artikelname' oder 'Artikelnummer' existiert und nicht leer ist
            if 'Artikelname' in df.columns:
                df = df[df['Artikelname'].str.strip() != '']
            elif 'Artikelnummer' in df.columns:
                df = df[df['Artikelnummer'].str.strip() != '']
            
            # Alle Zeilen, wo ALLES leer ist, entfernen
            df.dropna(how='all', inplace=True)
            
            return df
        except UnicodeDecodeError:
            continue
        except Exception as e:
            logging.error(f"❌ Fehler beim Lesen ({enc}): {e}")
            return None
            
    logging.error(f"❌ Konnte Datei nicht lesen (Alle Encodings fehlgeschlagen): {filepath}")
    return None

def check_data_quality(data):
    ignored_keys = ["Kategorie", "Produktname", "Bild_URL", "_Original_GTIN", "_Produktname", "_Artikelnummer", "Besonderheiten"]
    total_fields = 0
    na_fields = 0
    for key, value in data.items():
        if key in ignored_keys: continue
        total_fields += 1
        if str(value).lower().strip() in ["n/a", "na", "nein", "", "nicht verfügbar", "unknown"]:
            na_fields += 1
    if total_fields == 0: return True 
    if (na_fields / total_fields) > 0.5: return True
    return False

def append_to_retry_csv(row_data):
    file_exists = os.path.isfile(RETRY_CSV_FILE)
    with open(RETRY_CSV_FILE, mode='a', newline='', encoding='utf-8') as f:
        fieldnames = ['Artikelnummer', 'Artikelname', 'GTIN', 'EAN', 'HAN', 'Hersteller', 'Kategorie']
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction='ignore', delimiter=';')
        if not file_exists: writer.writeheader()
        row_dict = row_data.to_dict()
        if 'GTIN' not in row_dict and 'GTIN_Clean' in row_dict:
            row_dict['GTIN'] = row_dict['GTIN_Clean']
        writer.writerow(row_dict)

def process_dataframe(df, agent, forced_category=None, stop_event=None):
    total_items = len(df)
    if total_items == 0:
        logging.warning("⚠️  Leere Datei übersprungen.")
        return "OK"

    for index, row in df.iterrows():
        if stop_event and stop_event.is_set():
            logging.warning("\n🛑 VORGANG ABGEBROCHEN.")
            break

        name = row.get('Artikelname', 'Unbekannt')
        # Skip wenn Name leer ist (Sicherheitsnetz)
        if not name or str(name).strip() == "":
            continue

        gtin = str(row.get('GTIN', '')).replace('.0', '').strip()
        art_nr = row.get('Artikelnummer', row.get('ArtNr', row.get('SKU', '')))
        
        if art_nr and str(art_nr).strip() != "":
            safe_filename = re.sub(r'[\\/*?:"<>|]', "", str(art_nr)).strip().replace(" ", "_")
            log_prefix = f"({index + 1}/{total_items}) ArtNr: {safe_filename}"
        else:
            safe_filename = re.sub(r'[\\/*?:"<>|]', "", str(name)).replace(" ", "_")[:80]
            log_prefix = f"({index + 1}/{total_items}) {name[:20]}..."

        # Leere Filenames verhindern
        if not safe_filename:
            continue

        json_filename = f"{safe_filename}.json"
        json_path = os.path.join(OUTPUT_FOLDER, json_filename)
        
        cat_log = f" [Force: {forced_category}]" if forced_category else " [Auto-Router]"
        logging.info(f"🔍 {log_prefix}{cat_log} | Starte Suche...")

        if os.path.exists(json_path):
            print(f"⏭️  Bereits fertig.")
            continue

        prompt = get_prompt_by_category(name, gtin, forced_category=forced_category)

        try:
            response_text = agent.run(prompt)
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            
            if json_match:
                data = json.loads(json_match.group(0))
                
                data["_Original_GTIN"] = gtin
                data["_Produktname"] = name
                data["_Artikelnummer"] = str(art_nr) 
                
                search_name = data.get("Produktname", name)
                cat_found = forced_category if forced_category else data.get("Kategorie", "")
                image_url = find_product_image(search_name, category=cat_found)
                data["Bild_URL"] = image_url if image_url else ""
                
                is_bad = check_data_quality(data)
                if is_bad:
                    logging.warning(f"⚠️  QUALITÄTS-WARNUNG. -> Retry Liste.")
                    append_to_retry_csv(row)
                
                with open(json_path, "w", encoding="utf-8") as f:
                    json.dump(data, f, ensure_ascii=False, indent=4)
                
                if not is_bad: logging.info(f"✅ Gespeichert & Qualität OK.")
                
            else:
                log_error(name, gtin, "Kein JSON gefunden", raw_content=response_text)
                logging.error("❌ Kein JSON. -> Retry Liste.")
                append_to_retry_csv(row)

        except Exception as e:
            err_msg = str(e)
            logging.error(f"❌ Fehler: {err_msg}")
            log_error(name, gtin, f"Crash: {err_msg}")
            append_to_retry_csv(row)
            if "432" in err_msg or "quota" in err_msg.lower():
                logging.critical("\n🛑 TAVILY LIMIT ERREICHT.")
                return "STOP"

        time.sleep(1)
    return "OK"

def main(stop_event=None):
    setup_folders()
    agent = setup_agent()
    
    logging.info("🚀 Starte 'Folder-Mode' Verarbeitung...")
    
    # 1. Scanne ROOT (Unsortiert)
    if os.path.exists(INPUT_FOLDER):
        root_files = [f for f in os.listdir(INPUT_FOLDER) if f.endswith(".csv") and os.path.isfile(os.path.join(INPUT_FOLDER, f))]
        
        for csv_file in root_files:
            csv_path = os.path.join(INPUT_FOLDER, csv_file)
            logging.info(f"\n📂 Lade unsortierte Datei: {csv_file}")
            df = read_csv_robust(csv_path)
            if df is not None:
                status = process_dataframe(df, agent, forced_category=None, stop_event=stop_event)
                if status == "STOP": return

        # 2. Scanne UNTERORDNER (Sortiert)
        subdirs = [d for d in os.listdir(INPUT_FOLDER) if os.path.isdir(os.path.join(INPUT_FOLDER, d))]
        
        for subdir in subdirs:
            forced_cat = FOLDER_MAPPING.get(subdir)
            
            if not forced_cat:
                # Optional: Warnung auskommentieren, wenn dich andere Ordner nerven
                # logging.warning(f"⚠️  Ordner '{subdir}' nicht im Mapping erkannt.")
                continue
                
            subdir_path = os.path.join(INPUT_FOLDER, subdir)
            csv_files = [f for f in os.listdir(subdir_path) if f.endswith(".csv")]
            
            for csv_file in csv_files:
                csv_path = os.path.join(subdir_path, csv_file)
                logging.info(f"\n📂 Lade Kategorie-Datei ({forced_cat}): {subdir}/{csv_file}")
                
                df = read_csv_robust(csv_path)
                if df is not None:
                    status = process_dataframe(df, agent, forced_category=forced_cat, stop_event=stop_event)
                    if status == "STOP": return

    # Post-Processing
    print("\n" + "="*50)
    logging.info("🔄 Starte Post-Processing...")
    mapper = MarvinMapper(output_folder="output_JSON_Marvin")
    html_gen = None
    try:
        html_gen = HTMLGenerator(json_folder=OUTPUT_FOLDER, output_folder="output_HTML", template_path="templates/template.html")
    except: pass

    if os.path.exists(OUTPUT_FOLDER):
        for filename in os.listdir(OUTPUT_FOLDER):
            if filename.endswith(".json"):
                file_path = os.path.join(OUTPUT_FOLDER, filename)
                try:
                    with open(file_path, 'r', encoding='utf-8') as f: data = json.load(f)
                    html_c = html_gen.generate_single(filename) if html_gen else ""
                    mapper.create_json(file_path, data, html_content=html_c)
                except Exception as e:
                    logging.error(f"❌ Fehler Mapper {filename}: {e}")

    logging.info("✅ FERTIG.")

if __name__ == "__main__":
    main()