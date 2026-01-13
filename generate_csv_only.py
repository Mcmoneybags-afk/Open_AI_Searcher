import time
from modules.config import OUTPUT_FOLDER
from modules.html_generator import HTMLGenerator

def main():
    print("==========================================")
    print("   MANUELLER JTL-CSV EXPORT")
    print("==========================================")
    print("")
    
    # Wir nutzen dieselben Einstellungen wie in main.py
    # output_folder="output_HTML" ist der Standard-Ordner, wo deine HTMLs liegen
    try:
        generator = HTMLGenerator(
            json_folder=OUTPUT_FOLDER, 
            output_folder="output_HTML",
            template_path="templates/template.html"
        )

        # Ruft direkt die Export-Funktion auf, ohne vorher HTMLs neu zu generieren
        generator.create_jtl_export()
        
    except Exception as e:
        print(f"❌ Ein Fehler ist aufgetreten: {e}")

    print("")
    print("------------------------------------------")
    print("Das Fenster schließt sich in 5 Sekunden...")
    time.sleep(5)

if __name__ == "__main__":
    main()