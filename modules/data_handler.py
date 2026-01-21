import pandas as pd
import os
from .config import INPUT_FOLDER, INPUT_FILE

def load_csv_optimized():
    file_path = os.path.join(INPUT_FOLDER, INPUT_FILE)
    
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Die Datei {file_path} wurde nicht gefunden.")

    print(f"   📂 Lade Datei: {INPUT_FILE} ...")

    # --- 1. STRATEGIE: EXCEL (.xlsx / .xls) 📊 ---
    # Das ist der sicherste Weg gegen das "E+12"-Problem!
    if file_path.lower().endswith(('.xlsx', '.xls')):
        try:
            # dtype=str ist der Trick: Wir zwingen Python, ALLES als Text zu lesen.
            # Dadurch wird "4711..." nicht zu einer Zahl umgewandelt.
            df = pd.read_excel(file_path, dtype=str)
            
            # Spalten bereinigen (Leerzeichen/Anführungszeichen weg)
            df.columns = [str(c).strip().replace('"', '') for c in df.columns]
            df = df.dropna(how='all')
            
            # GTIN Spalten harmonisieren
            if 'GTIN' in df.columns and 'GTIN_Clean' not in df.columns:
                df['GTIN_Clean'] = df['GTIN'].fillna('')
            elif 'GTIN_Clean' not in df.columns:
                df['GTIN_Clean'] = ''
            
            print(f"   ✅ Excel-Datei erfolgreich geladen! ({len(df)} Zeilen)")
            return df
        except Exception as e:
            print(f"   ❌ Fehler beim Laden der Excel-Datei: {e}")
            raise ValueError("Konnte Excel-Datei nicht lesen. Sind 'openpyxl' und 'pandas' installiert?")

    # --- 2. STRATEGIE: CSV / TEXT (Robust gegen Formate) ---
    attempts = [
        {"encoding": "utf-8", "sep": ";"},
        {"encoding": "utf-8", "sep": ","},
        {"encoding": "utf-8", "sep": "\t"},  # Tab-getrennt (Deine Idee!)
        {"encoding": "latin1", "sep": ";"},   
        {"encoding": "latin1", "sep": ","},
        {"encoding": "latin1", "sep": "\t"},
        {"encoding": "cp1252", "sep": ";"},
        {"encoding": "cp1252", "sep": ","}
    ]

    for attempt in attempts:
        enc = attempt["encoding"]
        sep = attempt["sep"]
        
        try:
            # Auch hier: dtype=str verhindert wissenschaftliche Notation beim Einlesen
            df = pd.read_csv(file_path, sep=sep, encoding=enc, dtype=str)
            
            # Spalten bereinigen
            df.columns = [c.strip().replace('"', '') for c in df.columns]

            if 'Artikelname' in df.columns or 'Artikelnummer' in df.columns:
                print(f"   ✅ CSV/TXT geladen mit Encoding='{enc}' und Trenner='{repr(sep)}'")
                
                df = df.dropna(how='all')
                
                if 'GTIN' in df.columns and 'GTIN_Clean' not in df.columns:
                    df['GTIN_Clean'] = df['GTIN'].fillna('')
                elif 'GTIN_Clean' not in df.columns:
                    df['GTIN_Clean'] = ''
                
                return df
                
        except Exception:
            continue

    raise ValueError(f"CRITICAL: Die Datei konnte mit keinem gängigen Format (Excel, UTF-8/ANSI, Semikolon/Komma/Tab) gelesen werden.")