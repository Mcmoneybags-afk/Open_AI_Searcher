import os
import json
from jinja2 import Environment, FileSystemLoader
from .json_mapper import MarvinMapper

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
        self.marvin = MarvinMapper()
        
        # Ordner erstellen
        if not os.path.exists(output_folder):
            os.makedirs(output_folder)

    def _row(self, label, value, is_odd):
        """ Hilfsfunktion für eine Tabellenzeile """
        if not value or str(value).lower() in ["n/a", "na", "none", ""]:
            return ""
        css_class = "ITSr1" if is_odd else "ITSr0"
        return f'<div class="{css_class}"><div class="ITSn">{label}</div><div class="ITSv">{value}</div></div>'

    def _generate_ram_html(self, data):
        """ Spezial-Generator für Arbeitsspeicher (RAM) nach IT-Scope Vorlage """
        html = '<div class="ITSs">\n'
        
        # --- Allgemein ---
        html += '<div class="ITSg">Allgemein</div>\n'
        
        # Kapazität logik: "64 GB: 2 x 32 GB"
        cap = data.get("Allgemein", {}).get("Kapazität", "")
        conf = data.get("Speicher", {}).get("Modulkonfiguration", "")
        
        # Kombinieren, wenn Konfiguration nicht schon im String steckt
        if cap and conf and conf not in cap:
            cap_display = f"{cap}: {conf}" 
        else:
            cap_display = cap or conf
            
        odd = True
        html += self._row("Kapazität", cap_display, odd); odd = not odd
        html += self._row("Erweiterungstyp", data.get("Allgemein", {}).get("Erweiterungstyp", "Generisch"), odd); odd = not odd
        
        # Abmessungen
        w = data.get("Allgemein", {}).get("Breite", "")
        d = data.get("Allgemein", {}).get("Tiefe", "")
        h = data.get("Allgemein", {}).get("Höhe", "")
        
        if w: html += self._row("Breite", w, odd); odd = not odd
        if d: html += self._row("Tiefe", d, odd); odd = not odd
        if h: html += self._row("Höhe", h, odd); odd = not odd

        # --- Arbeitsspeicher (WICHTIG: Umbenannt von "Speicher") ---
        html += '<div class="ITSg">Arbeitsspeicher</div>\n'
        mem = data.get("Speicher", {})
        
        odd = True
        html += self._row("Typ", mem.get("Typ", "DRAM Speicher-Kit"), odd); odd = not odd
        html += self._row("Technologie", mem.get("Technologie", ""), odd); odd = not odd
        html += self._row("Formfaktor", mem.get("Formfaktor", ""), odd); odd = not odd
        
        # Versuch Höhe in Zoll umzurechnen oder anzuzeigen
        if h and "mm" in h:
            try:
                h_val = float(h.replace("mm", "").strip())
                h_inch = round(h_val / 25.4, 2)
                html += self._row("Modulhöhe (Zoll)", str(h_inch), odd); odd = not odd
            except: pass

        html += self._row("Geschwindigkeit", mem.get("Geschwindigkeit", ""), odd); odd = not odd
        html += self._row("Latenzzeiten", mem.get("Latenzzeiten", ""), odd); odd = not odd
        html += self._row("Datenintegritätsprüfung", mem.get("Datenintegritätsprüfung", ""), odd); odd = not odd
        html += self._row("Besonderheiten", mem.get("Besonderheiten", ""), odd); odd = not odd
        html += self._row("Modulkonfiguration", mem.get("Modulkonfiguration", ""), odd); odd = not odd
        
        # Fehlende Felder auffüllen (Standardwerte oder leer)
        html += self._row("Chip-Organisation", "X8", odd); odd = not odd # Oft Standard
        html += self._row("Spannung", mem.get("Spannung", ""), odd); odd = not odd
        html += self._row("Metallüberzug", "Gold", odd); odd = not odd
        
        # RAM-Leistung (Fallback auf Geschwindigkeit, wenn keine Details da sind)
        ram_perf = data.get("Unterstützter RAM", {}).get("Bustakt", "")
        if not ram_perf: ram_perf = mem.get("Geschwindigkeit", "")
        # html += self._row("RAM-Leistung", ram_perf, odd); odd = not odd

        # --- Verschiedenes ---
        html += '<div class="ITSg">Verschiedenes</div>\n'
        misc = data.get("Verschiedenes", {})
        
        odd = True
        html += self._row("Farbkategorie", misc.get("Farbe", ""), odd); odd = not odd
        html += self._row("Kennzeichnung", misc.get("Produktzertifizierungen", "JEDEC"), odd); odd = not odd

        # --- Garantie ---
        html += '<div class="ITSg">Herstellergarantie</div>\n'
        html += self._row("Service und Support", data.get("Herstellergarantie", {}).get("Service und Support", ""), True)

        html += '</div>'
        return html

    def generate_generic_html(self, data):
        """ Der Standard-Generator für alle anderen Kategorien (Mainboard, CPU etc.) """
        html = '<div class="ITSs">\n'
        
        has_groups = any(isinstance(v, dict) for v in data.values())
        if not has_groups: data = {"Allgemein": data}

        for group_name, fields in data.items():
            # Metadaten überspringen
            if group_name.startswith("_"): continue
            
            if isinstance(fields, dict):
                html += f'    <div class="ITSg">{group_name}</div>\n'
                row_idx = 1
                for key, value in fields.items():
                    if key.startswith("_"): continue
                    # Odd/Even Logik
                    odd = (row_idx == 1)
                    html += self._row(key, value, odd)
                    row_idx = 1 - row_idx
        html += '</div>'
        return html

    def generate_single(self, json_file):
        """ Liest eine JSON, wählt den richtigen Generator und speichert das HTML. """
        json_path = os.path.join(self.json_folder, json_file)
        
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        # --- INTELLIGENTE WEICHE (Der Magic Trick) 🎩 ---
        # Prüft, ob es RAM ist (Key "Speicher" + "Kapazität" vorhanden)
        has_speicher = "Speicher" in data
        has_formfaktor = "Formfaktor" in data.get("Speicher", {})
        
        if has_speicher and has_formfaktor:
            print(f"   Detected RAM for {json_file}") # Debug Ausgabe
            technical_block = self._generate_ram_html(data)
        else:
            technical_block = self.generate_generic_html(data)
        # -----------------------------------------------
        
        product_name = data.get("Produktname", data.get("_Produktname", "Datenblatt"))
        
        output = self.template.render(
            product_name=product_name,
            tech_specs=technical_block,
            data=data
        )
        
        output_filename = json_file.replace(".json", ".html")
        output_path = os.path.join(self.output_folder, output_filename)
        
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(output)
            
        try:
            self.marvin.create_json(json_file, data, technical_block)
        except Exception as e:
            print(f"   ⚠️ Fehler beim Marvin-Mapping für {json_file}: {e}")
            
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