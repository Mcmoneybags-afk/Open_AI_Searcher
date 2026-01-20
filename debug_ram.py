import json
import os
from modules.html_generator import HTMLGenerator

# Pfad zur problematischen JSON Datei (pass ggf. den Dateinamen an!)
# Ich nehme die Artikelnummer aus deinem Beispiel: 106548
json_file = "106548.json" 
json_path = os.path.join("output_JSON", json_file) # Oder wo deine JSONs liegen

print(f"--- 🕵️‍♂️ RAM DIAGNOSE FÜR {json_file} ---")

if not os.path.exists(json_path):
    # Fallback: Suche irgendeine JSON im Ordner
    folder = "output_JSON" # Passe Pfad an falls nötig (z.B. input_csv/.../...)
    if os.path.exists(folder):
        files = [f for f in os.listdir(folder) if f.endswith(".json")]
        if files:
            json_path = os.path.join(folder, files[0])
            print(f"⚠️ Test-Datei nicht gefunden, nehme stattdessen: {files[0]}")
        else:
            print("❌ Keine JSON Dateien gefunden!")
            exit()
    else:
        print(f"❌ Ordner {folder} nicht gefunden.")
        exit()

with open(json_path, "r", encoding="utf-8") as f:
    data = json.load(f)

print("1. Prüfe Struktur...")
if "Speicher" in data:
    print("   ✅ Block 'Speicher' gefunden.")
    keys = list(data["Speicher"].keys())
    print(f"   ℹ️ Enthaltene Keys: {keys}")
    
    if "Formfaktor" in data["Speicher"]:
        print("   ✅ Key 'Formfaktor' gefunden! -> SOLLTE RAM MODUS SEIN 🚀")
        
        # Wir simulieren den Generator
        gen = HTMLGenerator(".", ".")
        html = gen._generate_ram_html(data)
        
        if "Arbeitsspeicher" in html:
            print("   ✅ Generator erzeugt korrekten Titel 'Arbeitsspeicher'.")
        else:
            print("   ❌ Generator erzeugt FALSCHEN Titel (Bug in _generate_ram_html).")
            
        if "32 GB: 2 x 16 GB" in html or "2 x 16 GB" in html:
             print("   ✅ Kapazität wird kombiniert.")
        else:
             print("   ⚠️ Kapazität nicht kombiniert.")

    else:
        print("   ❌ Key 'Formfaktor' NICHT gefunden.")
        # Check auf ähnliche Schreibweisen
        for k in keys:
            if k.lower() == "formfaktor":
                print(f"      💡 HINWEIS: Gefunden wurde '{k}' (Groß/Kleinschreibung beachten!)")
else:
    print("   ❌ Block 'Speicher' NICHT gefunden.")

print("-" * 30)