from modules.config import OUTPUT_FOLDER
from modules.html_generator import HTMLGenerator

def main():
    print("🚀 Starte manuelle HTML-Generierung...")
    
    try:
        generator = HTMLGenerator(
            json_folder=OUTPUT_FOLDER,       
            output_folder="output_HTML",     
            template_path="templates/template.html"
        )
        
        generator.generate_all()
        
    except Exception as e:
        print(f"❌ Ein Fehler ist aufgetreten: {e}")

if __name__ == "__main__":
    main()