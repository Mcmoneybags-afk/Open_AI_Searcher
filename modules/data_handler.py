import pandas as pd
import os
from .config import INPUT_FOLDER, INPUT_FILE

def load_csv_optimized():
    file_path = os.path.join(INPUT_FOLDER, INPUT_FILE)
    
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Die Datei {file_path} wurde nicht gefunden.")


    attempts = [
        {"encoding": "utf-8", "sep": ";"},
        {"encoding": "utf-8", "sep": ","},
        {"encoding": "latin1", "sep": ";"},   
        {"encoding": "latin1", "sep": ","},
        {"encoding": "cp1252", "sep": ";"},
        {"encoding": "cp1252", "sep": ","}
    ]

    for attempt in attempts:
        enc = attempt["encoding"]
        sep = attempt["sep"]
        
        try:
            # Versuch, die Datei komplett zu laden
            df = pd.read_csv(file_path, sep=sep, encoding=enc, dtype=str)
            
            # Spalten bereinigen (Leerzeichen entfernen)
            df.columns = [c.strip().replace('"', '') for c in df.columns]

            # PRÜFUNG: Ist das die richtige Datei?
            # Wir akzeptieren sie nur, wenn "Artikelname" ODER "Artikelnummer" gefunden wurde
            if 'Artikelname' in df.columns:
                print(f"✅ Erfolg! CSV geladen mit Encoding='{enc}' und Trenner='{sep}'")
                
                df = df.dropna(how='all')
                
                if 'GTIN' in df.columns and 'GTIN_Clean' not in df.columns:
                    df['GTIN_Clean'] = df['GTIN'].fillna('')
                elif 'GTIN_Clean' not in df.columns:
                    df['GTIN_Clean'] = ''
                
                return df
                
        except Exception:
            # Falsches Encoding oder falscher Trenner ? ==>  Einfach weitermachen (continue)
            continue

    # Wenn wir hier ankommen, hat nichts funktioniert
    raise ValueError(f"CRITICAL: Die Datei konnte mit keinem gängigen Format (UTF-8/ANSI, Semikolon/Komma) gelesen werden.")