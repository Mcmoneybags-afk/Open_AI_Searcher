import pandas as pd
import os
from .config import INPUT_FOLDER, INPUT_FILE

def load_csv_optimized():
    file_path = os.path.join(INPUT_FOLDER, INPUT_FILE)
    
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Die Datei {file_path} wurde nicht gefunden.")

    # --- UPDATE: EXCEL SUPPORT (.xlsx / .xls) 📊 ---
    # Falls du die Datei sicherheitshalber als Excel gespeichert hast:
    if file_path.lower().endswith(('.xlsx', '.xls')):
        try:
            print(f"   📊 Lade Excel-Datei: {INPUT_FILE} ...")
            # dtype=str ist hier der Trick: Es zwingt Python, alles als Text zu lesen!
            df = pd.read_excel(file_path, dtype=str)
            
            # Spalten bereinigen
            df.columns = [str(c).strip().replace('"', '') for c in df.columns]
            df = df.dropna(how='all')
            
            # GTIN Clean Logic
            if 'GTIN' in df.columns and 'GTIN_Clean' not in df.columns:
                df['GTIN_Clean'] = df['GTIN'].fillna('')
            elif 'GTIN_Clean' not in df.columns:
                df['GTIN_Clean'] = ''
            
            print(f"   ✅ Excel erfolgreich geladen! ({len(df)} Zeilen)")
            return df
        except Exception as e:
            print(f"   ❌ Fehler beim Laden der Excel-Datei: {e}")
            # Falls es scheitert, machen wir unten weiter (unwahrscheinlich, aber sicher ist sicher)

    # --- CSV / TEXT LOADER (Robust gegen Formate) ---
    attempts = [
        {"encoding": "utf-8", "sep": ";"},
        {"encoding": "utf-8", "sep": ","},
        {"encoding": "utf-8", "sep": "\t"},  # Tab-getrennt (deine Idee!)
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
            # dtype=str verhindert, dass "4711..." wissenschaftlich verformt wird
            df = pd.read_csv(file_path, sep=sep, encoding=enc, dtype=str)
            
            # Spalten bereinigen
            df.columns = [c.strip().replace('"', '') for c in df.columns]

            if 'Artikelname' in df.columns:
                print(f"✅ Erfolg! CSV/TXT geladen mit Encoding='{enc}' und Trenner='{repr(sep)}'")
                
                df = df.dropna(how='all')
                
                if 'GTIN' in df.columns and 'GTIN_Clean' not in df.columns:
                    df['GTIN_Clean'] = df['GTIN'].fillna('')
                elif 'GTIN_Clean' not in df.columns:
                    df['GTIN_Clean'] = ''
                
                return df
                
        except Exception:
            continue

    raise ValueError(f"CRITICAL: Die Datei konnte mit keinem gängigen Format (Excel, UTF-8/ANSI, Semikolon/Komma/Tab) gelesen werden.")