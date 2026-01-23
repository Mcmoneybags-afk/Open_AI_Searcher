import os
import pandas as pd
import shutil

# --- KONFIGURATION ---
# Die Datei, die wir sortieren wollen (liegt im Master_Excel Ordner)
INPUT_FILE = "Master_Excel/artikel.xlsx"

# Wohin soll sortiert werden?
OUTPUT_BASE_FOLDER = "input_csv"

# --- REGELWERK: Welches Keyword gehört in welchen Ordner? ---
# Die Ordnernamen müssen exakt zu deinem FOLDER_MAPPING in main.py passen!
KEYWORD_RULES = {
    "02_Arbeitsspeicher": ["ddr", "dimm", "sodimm", "ram ", "memory kit", "cl16", "cl30", "cl40", "xmp", "expo"],
    "03_Gehaeuse": ["gehäuse", "tower", "case", "midi", "meshify", "pop air", "define", "o11", "north", "chassis"],
    "04_Grafikkarten": ["rtx", "gtx", "radeon", "rx 7", "rx 6", "geforce", "gpu", "graphics", "vga", "4070", "4080", "4090", "7900", "7800"],
    "05_Mainboards": ["mainboard", "motherboard", "z790", "b650", "x670", "b550", "b760", "lga1700", "am5", "am4", "sockel", "wifi"],
    "06_Netzteile": ["netzteil", "psu", "power supply", "watt", "80+", "80 plus", "gold", "platinum", "titanium", "be quiet! pure power", "corsair rm"],
    "07_Prozessor_AMD": ["ryzen", "threadripper", "amd cpu", "am5 cpu", "am4 cpu"],
    "08_Prozessor_Intel": ["intel core", "i9-", "i7-", "i5-", "i3-", "intel cpu", "lga1700 cpu"],
    "09_CPU_Kuehler": ["cpu kühler", "cpu cooler", "luftkühler", "air cooler", "ak620", "dark rock", "assassin"],
    "10_Monitore": ["monitor", "display", "tft", "oled", "wqhd", "uhd", "144hz", "165hz", "240hz", "samsung odyssey", "lg ultragear"],
    "11_Gehaeuseluefter": ["gehäuselüfter", "case fan", "lüfter 120", "lüfter 140", "pwm fan", "argb fan", "uni fan"],
    "13_Speicher": ["ssd", "hdd", "festplatte", "m.2", "nvme", "sata", "wd red", "samsung 990", "lexar nm", "crucial p3"],
    "14_Eingabegeraete": ["maus", "mouse", "tastatur", "keyboard", "keypad", "mechanisch", "gaming maus"],
    "15_Kabel_Adapter": ["kabel", "cable", "adapter", "hdmi", "displayport", "usb-c", "verlängerung"],
    "20_Netzwerkkarten": ["netzwerkkarte", "pci-e netzwerk", "10gbit", "ethernet adapter"],
    "22_Software": ["windows", "office", "lizenz", "esd", "norton", "kaspersky", "mcafee", "adobe", "software"],
    "23_Wasserkuehlungen": ["wasserkühlung", "aio", "liquid cooler", "water cooling", "kraken", "corsair h", "arctic liquid"],
    "36_Headsets": ["headset", "kopfhörer", "headphones", "earbuds"],
    "42_USB_Sticks": ["usb stick", "flash drive", "pen drive", "speicherstick"]
}

def sort_master_excel():
    print(f"🚀 Starte Smart-Sorter für: {INPUT_FILE}")
    
    # 1. Datei laden
    try:
        # Check ob Excel oder CSV
        if INPUT_FILE.endswith(".xlsx"):
            df = pd.read_excel(INPUT_FILE, dtype=str).fillna("")
        else:
            df = pd.read_csv(INPUT_FILE, dtype=str, sep=None, engine='python').fillna("")
            
        print(f"📦 {len(df)} Artikel geladen.")
    except Exception as e:
        print(f"❌ Fehler beim Laden: {e}")
        return

    # Dictionary um DataFrames für jede Kategorie zu sammeln
    sorted_data = {cat: [] for cat in KEYWORD_RULES.keys()}
    sorted_data["Unsortiert"] = [] # Reste-Rampe

    # 2. Sortier-Logik
    for index, row in df.iterrows():
        # Namen normalisieren (alles klein) für Suche
        name_raw = str(row.get('Produktname', row.get('Artikelname', ''))).lower()
        
        # Priorisierte Suche: Zuerst spezifische, dann generische
        found_category = None
        
        for category, keywords in KEYWORD_RULES.items():
            for kw in keywords:
                # WICHTIG: Wortgrenzen beachten ist hier schwer, einfache Suche reicht meist
                if kw in name_raw:
                    found_category = category
                    break
            if found_category:
                break
        
        if found_category:
            sorted_data[found_category].append(row)
        else:
            sorted_data["Unsortiert"].append(row)

    # 3. Speichern in die Ordner
    print("\n💾 Speichere sortierte Dateien...")
    
    for category, rows in sorted_data.items():
        if not rows: continue # Leere Kategorien überspringen
        
        # Ziel-Ordner bestimmen
        if category == "Unsortiert":
            # Unsortierte kommen direkt in input_csv (Main Script nutzt dann Auto-Router)
            target_dir = OUTPUT_BASE_FOLDER
            filename = "reste_unsortiert.csv"
        else:
            # Sortierte kommen in Unterordner
            target_dir = os.path.join(OUTPUT_BASE_FOLDER, category)
            filename = f"auto_sorted_{category}.csv"
        
        # Ordner erstellen falls nicht existiert
        os.makedirs(target_dir, exist_ok=True)
        
        # DataFrame erstellen und speichern
        df_cat = pd.DataFrame(rows)
        save_path = os.path.join(target_dir, filename)
        
        # Als CSV speichern (UTF-8, Semikolon getrennt für Excel-Kompatibilität)
        df_cat.to_csv(save_path, index=False, sep=';', encoding='utf-8-sig')
        
        print(f"   📂 {category}: {len(rows)} Artikel -> {save_path}")

    print("\n✅ Fertig! Du kannst jetzt 'main.py' starten.")

if __name__ == "__main__":
    sort_master_excel()