import os
import json
from jinja2 import Environment, FileSystemLoader
from .json_mapper import MarvinMapper  # <--- NEU: Import des Mappers

class HTMLGenerator:
    def __init__(self, json_folder, output_folder, template_path="templates/template.html"):
        self.json_folder = json_folder
        self.output_folder = output_folder
        self.template_dir = os.path.dirname(template_path)
        self.template_name = os.path.basename(template_path)
        
        # Jinja2 Setup
        self.env = Environment(loader=FileSystemLoader(self.template_dir))
        self.template = self.env.get_template(self.template_name)
        
        # Marvin Mapper Initialisieren
        self.marvin = MarvinMapper() # <--- NEU: Mapper Instanz erstellen
        
        # Ordner erstellen
        if not os.path.exists(output_folder):
            os.makedirs(output_folder)

    def generate_jtl_html_block(self, data):
        """ 
        Baut das JTL-spezifische HTML (ITS-Klassen) aus dem hierarchischen JSON.
        Erzeugt KEIN ganzes HTML-Dokument, sondern nur den <div class="ITSs">...</div> Block.
        """
        
        # Start Container
        html = '<div class="ITSs">\n'
        
        # Wir müssen sicherstellen, dass wir durch die Gruppen iterieren
        # Fallback: Falls das JSON flach ist (alte Dateien), behandeln wir alles als eine Gruppe
        has_groups = any(isinstance(v, dict) for v in data.values())
        
        if not has_groups:
            # Alte Logik (Fallback) -> Alles in eine "Allgemein" Gruppe packen
            data = {"Allgemein": data}

        for group_name, fields in data.items():
            # Metadaten (die mit _ beginnen) überspringen
            if group_name.startswith("_"): continue
            
            # Sicherheitscheck: Ist der Inhalt wirklich eine Gruppe (Dict)?
            if isinstance(fields, dict):
                # 1. Graue Überschrift (ITSg)
                html += f'    <div class="ITSg">{group_name}</div>\n'
                
                # Zeilenzähler für Zebra-Muster (1 = Hell, 0 = Dunkel/Anders)
                # JTL nutzt ITSr1 und ITSr0 abwechselnd
                row_idx = 1
                
                for key, value in fields.items():
                    if key.startswith("_"): continue # Metadaten in der Gruppe überspringen
                    
                    # Zebra Klasse
                    row_class = f"ITSr{row_idx}"
                    
                    html += f'    <div class="{row_class}">\n'
                    html += f'        <div class="ITSn">{key}</div>\n'
                    html += f'        <div class="ITSv">{value}</div>\n'
                    html += f'    </div>\n'
                    
                    # Flip Flop (1 -> 0, 0 -> 1)
                    row_idx = 1 - row_idx

        html += '</div>'
        return html

    def generate_single(self, json_file):
        """ Liest eine JSON, baut den Block und speichert das HTML. """
        json_path = os.path.join(self.json_folder, json_file)
        
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        # 1. Den komplexen HTML-Block bauen (Python Logic)
        technical_block = self.generate_jtl_html_block(data)
        
        # 2. Metadaten für den Header extrahieren (falls vorhanden)
        product_name = data.get("Produktname", data.get("_Produktname", "Datenblatt"))
        
        # 3. In das Template einfügen (Jinja2 Logic)
        # Wir übergeben den fertigen Block als 'tech_specs'
        output = self.template.render(
            product_name=product_name,
            tech_specs=technical_block,
            original_data=data # Falls wir im Template noch was anderes brauchen
        )
        
        # Speichern
        output_filename = json_file.replace(".json", ".html")
        output_path = os.path.join(self.output_folder, output_filename)
        
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(output)
            
        # --- NEU: MARVIN JSON ERSTELLEN ---
        # Wir übergeben das Original-JSON und den generierten HTML-Block (für marketingDesc)
        try:
            self.marvin.create_json(json_file, data, technical_block)
        except Exception as e:
            print(f"   ⚠️ Fehler beim Marvin-Mapping für {json_file}: {e}")
        # ----------------------------------
            
        return output_path

    def generate_all(self):
        print(f"🔄 Generiere HTMLs aus {self.json_folder}...")
        files = [f for f in os.listdir(self.json_folder) if f.endswith('.json')]
        
        if not files:
            print("⚠️ Keine JSON-Dateien gefunden.")
            return

        for f in files:
            try:
                self.generate_single(f)
                print(f" - {f} -> HTML & Marvin-JSON ✅")
            except Exception as e:
                print(f"❌ Fehler bei {f}: {e}")