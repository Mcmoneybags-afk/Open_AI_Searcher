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

    def _escape(self, text):
        """ Ersetzt Umlaute und Sonderzeichen für exakte Shop-Kompatibilität """
        if not text: return ""
        text = str(text)
        replacements = {
            "ä": "&auml;", "ö": "&ouml;", "ü": "&uuml;", "ß": "&szlig;",
            "Ä": "&Auml;", "Ö": "&Ouml;", "Ü": "&Uuml;",
            ":": "&colon;" 
        }
        for k, v in replacements.items():
            text = text.replace(k, v)
        return text

    def _row(self, label, value, is_odd):
        """ Hilfsfunktion für eine Tabellenzeile im exakten ITS-Format """
        if not value or str(value).lower() in ["n/a", "na", "none", ""]:
            return ""
        
        # Umlaute ersetzen
        label_safe = self._escape(label)
        value_safe = self._escape(value)
        
        # SPEZIAL 1: " GB" durch "&nbsp;GB" ersetzen (RAM/Speicher)
        value_safe = value_safe.replace(" GB", "&nbsp;GB")
        
        # SPEZIAL 2: Trenner "¦" durch HTML-Umbruch ersetzen
        if "¦" in value_safe:
            value_safe = value_safe.replace("¦", " <br /> ")
        
        css_class = "ITSr1" if is_odd else "ITSr0"
        
        return f'''
<div class="{css_class}">
<div class="ITSn">{label_safe}</div>

<div class="ITSv">{value_safe}</div>
</div>
'''

    def _generate_ram_html(self, data):
        """ Spezial-Generator für Arbeitsspeicher (RAM) """
        html = '<div class="ITSs">\n'
        
        # --- Allgemein ---
        html += '<div class="ITSg">Allgemein</div>\n'
        
        cap = data.get("Allgemein", {}).get("Kapazität", "")
        conf = data.get("Speicher", {}).get("Modulkonfiguration", "")
        
        if cap and conf and conf not in cap:
            cap_display = f"{cap} + {conf}" 
        else:
            cap_display = cap or conf
            
        odd = True
        html += self._row("Kapazität", cap_display, odd); odd = not odd
        html += self._row("Erweiterungstyp", data.get("Allgemein", {}).get("Erweiterungstyp", "Generisch"), odd); odd = not odd
        
        w = data.get("Allgemein", {}).get("Breite", "")
        d = data.get("Allgemein", {}).get("Tiefe", "")
        h = data.get("Allgemein", {}).get("Höhe", "")
        
        if w: html += self._row("Breite", w, odd); odd = not odd
        if d: html += self._row("Tiefe", d, odd); odd = not odd
        if h: html += self._row("Höhe", h, odd); odd = not odd

        # --- Arbeitsspeicher ---
        html += '\n<div class="ITSg">Arbeitsspeicher</div>\n'
        mem = data.get("Speicher", {})
        
        odd = True
        html += self._row("Typ", mem.get("Typ", "DRAM Speicher-Kit"), odd); odd = not odd
        html += self._row("Technologie", mem.get("Technologie", ""), odd); odd = not odd
        html += self._row("Formfaktor", mem.get("Formfaktor", ""), odd); odd = not odd
        
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
        
        html += self._row("Chip-Organisation", "X8", odd); odd = not odd
        html += self._row("Spannung", mem.get("Spannung", ""), odd); odd = not odd
        html += self._row("Metallüberzug", "Gold", odd); odd = not odd
        
        # --- Verschiedenes ---
        html += '\n<div class="ITSg">Verschiedenes</div>\n'
        misc = data.get("Verschiedenes", {})
        
        odd = True
        html += self._row("Farbkategorie", misc.get("Farbe", ""), odd); odd = not odd
        html += self._row("Kennzeichnung", misc.get("Produktzertifizierungen", "JEDEC"), odd); odd = not odd

        # --- Garantie ---
        html += '\n<div class="ITSg">Herstellergarantie</div>\n'
        html += self._row("Service und Support", data.get("Herstellergarantie", {}).get("Service und Support", ""), True)

        html += '</div>'
        return html

    def _generate_case_html(self, data):
        """ Spezial-Generator für PC-Gehäuse """
        html = '<div class="ITSs">\n'

        # 1. Allgemein
        html += '<div class="ITSg">Allgemein</div>\n'
        gen = data.get("Allgemein", {})
        odd = True
        
        keys_allgemein = [
            "GTIN", "EAN", "GTIN_Gefunden",
            "Formfaktor", "Seitenplatte mit Fenster", "Seitliches Plattenmaterial mit Fenster",
            "Max. Mainboard-Größe", "Unterstützte Motherboards", "Anzahl interner Einbauschächte",
            "Integrierte Peripheriegeräte", "Produktmaterial", "Farbe", "Kühlsystem",
            "Max. Höhe des CPU-Kühlers", "Maximale Länge Videokarte", "Maximallänge der Stromversorgung",
            "Systemgehäuse-Merkmale"
        ]
        
        for k in keys_allgemein:
            val = gen.get(k)
            if val:
                html += self._row(k, val, odd)
                odd = not odd

        # 2. Erweiterung/Konnektivität
        conn = data.get("Erweiterung / Konnektivität", {})
        if not conn: conn = data.get("Erweiterung/Konnektivität", {}) 
        
        if conn:
            html += '\n<div class="ITSg">Erweiterung/Konnektivität</div>\n'
            keys_conn = ["Erweiterungseinschübe", "Erweiterungssteckplätze", "Schnittstellen"]
            for k in keys_conn:
                val = conn.get(k)
                if val:
                    html += self._row(k, val, odd)
                    odd = not odd
        
        # 3. Stromversorgung
        power = data.get("Stromversorgung", {})
        if power:
            html += '\n<div class="ITSg">Stromversorgung</div>\n'
            keys_power = ["Stromversorgungsgerät", "Max. unterstützte Anzahl", "Spezifikationseinhaltung"]
            for k in keys_power:
                val = power.get(k)
                if val:
                    html += self._row(k, val, odd)
                    odd = not odd

        # 4. Abmessungen und Gewicht
        dims = data.get("Abmessungen und Gewicht", {})
        if dims:
            html += '\n<div class="ITSg">Abmessungen und Gewicht</div>\n'
            keys_dims = ["Breite", "Tiefe", "Höhe", "Gewicht"]
            for k in keys_dims:
                val = dims.get(k)
                if val:
                    html += self._row(k, val, odd)
                    odd = not odd

        # 5. Verschiedenes
        misc = data.get("Verschiedenes", {})
        if misc:
            html += '\n<div class="ITSg">Verschiedenes</div>\n'
            for k, v in misc.items():
                 html += self._row(k, v, odd)
                 odd = not odd

        # 6. Garantie
        warr = data.get("Herstellergarantie", {})
        if warr:
            html += '\n<div class="ITSg">Herstellergarantie</div>\n'
            html += self._row("Service und Support", warr.get("Service und Support"), True)

        html += '</div>'
        return html

    def _generate_gpu_html(self, data):
        """ Spezial-Generator für Grafikkarten (GPU) """
        html = '<div class="ITSs">\n'

        # 1. Allgemein
        html += '<div class="ITSg">Allgemein</div>\n'
        gen = data.get("Allgemein", {})
        odd = True
        
        keys_gen = [
            "Gerätetyp", "Bustyp", "Grafikprozessor", "Core Clock", "Boost-Takt",
            "Streamprozessoren", "CUDA-Kerne", "Max Auflösung", 
            "Anzahl der max. unterstützten Bildschirme", "Schnittstellendetails",
            "API-Unterstützung", "Besonderheiten"
        ]
        
        for k in keys_gen:
            val = gen.get(k)
            if val:
                html += self._row(k, val, odd)
                odd = not odd

        # 2. Arbeitsspeicher
        mem = data.get("Arbeitsspeicher", {})
        if mem:
            html += '\n<div class="ITSg">Arbeitsspeicher</div>\n'
            keys_mem = ["Grösse", "Technologie", "Speichergeschwindigkeit", "Busbreite"]
            for k in keys_mem:
                val = mem.get(k)
                if val:
                    html += self._row(k, val, odd)
                    odd = not odd

        # 3. Systemanforderungen
        sys = data.get("Systemanforderungen", {})
        if sys:
            html += '\n<div class="ITSg">Systemanforderungen</div>\n'
            keys_sys = ["Erfoderliche Leistungsversorgung", "Zusätzliche Anforderungen"]
            for k in keys_sys:
                val = sys.get(k)
                if val:
                    html += self._row(k, val, odd)
                    odd = not odd

        # 4. Verschiedenes
        misc = data.get("Verschiedenes", {})
        dims = data.get("Abmessungen und Gewicht", {})
        
        if misc or dims:
            html += '\n<div class="ITSg">Verschiedenes</div>\n'
            
            keys_misc = ["Zubehör im Lieferumfang", "Kennzeichnung", "Leistungsaufnahme im Betrieb"]
            for k in keys_misc:
                val = misc.get(k)
                if val:
                    html += self._row(k, val, odd)
                    odd = not odd
            
            dim_keys = ["Breite", "Tiefe", "Höhe", "Gewicht"]
            for k in dim_keys:
                val = misc.get(k) or dims.get(k)
                if val:
                    html += self._row(k, val, odd)
                    odd = not odd

        # 5. Garantie
        warr = data.get("Herstellergarantie", {})
        if warr:
            html += '\n<div class="ITSg">Herstellergarantie</div>\n'
            html += self._row("Service und Support", warr.get("Service und Support"), True)

        html += '</div>'
        return html

    def _generate_mainboard_html(self, data):
        """ Spezial-Generator für Mainboards """
        html = '<div class="ITSs">\n'

        # 1. Allgemein
        html += '<div class="ITSg">Allgemein</div>\n'
        gen = data.get("Allgemein", {})
        odd = True
        keys_gen = ["Produkttyp", "Chipsatz", "Prozessorsockel", "Max. Anz. Prozessoren", "Kompatible Prozessoren"]
        for k in keys_gen:
            val = gen.get(k)
            if val:
                html += self._row(k, val, odd)
                odd = not odd

        # 2. Unterstützter RAM
        ram = data.get("Unterstützter RAM", {})
        if ram:
            html += '\n<div class="ITSg">Unterstützter RAM</div>\n'
            keys_ram = ["Max. Größe", "Technologie", "Bustakt", "Unterstützte RAM-Integritätsprüfung", "Registriert oder gepuffert", "Besonderheiten"]
            for k in keys_ram:
                val = ram.get(k)
                if val:
                    html += self._row(k, val, odd)
                    odd = not odd

        # 3. Audio
        audio = data.get("Audio", {})
        if audio:
            html += '\n<div class="ITSg">Audio</div>\n'
            keys_audio = ["Typ", "Audio Codec", "Kompatibilität"]
            for k in keys_audio:
                val = audio.get(k)
                if val:
                    html += self._row(k, val, odd)
                    odd = not odd

        # 4. LAN
        lan = data.get("LAN", {})
        if lan:
            html += '\n<div class="ITSg">LAN</div>\n'
            keys_lan = ["Netzwerkcontroller", "Netzwerkschnittstellen"]
            for k in keys_lan:
                val = lan.get(k)
                if val:
                    html += self._row(k, val, odd)
                    odd = not odd

        # 5. Erweiterung/Konnektivität
        conn = data.get("Erweiterung/Konnektivität", data.get("Erweiterung / Konnektivität", {}))
        if conn:
            html += '\n<div class="ITSg">Erweiterung/Konnektivität</div>\n'
            # Hier haben wir "Schnittstellen" (allgemein) und "Interne Schnittstellen" unterschieden
            keys_conn = ["Erweiterungssteckplätze", "Speicherschnittstellen", "Schnittstellen", "Schnittstellen (Rückseite)", "Interne Schnittstellen", "Stromanschlüsse"]
            for k in keys_conn:
                val = conn.get(k)
                if val:
                    html += self._row(k, val, odd)
                    odd = not odd

        # 6. Besonderheiten
        feat = data.get("Besonderheiten", {})
        if feat:
            html += '\n<div class="ITSg">Besonderheiten</div>\n'
            keys_feat = ["BIOS-Typ", "BIOS-Funktionen", "Sleep / Wake up", "Hardwarefeatures"]
            for k in keys_feat:
                val = feat.get(k)
                if val:
                    html += self._row(k, val, odd)
                    odd = not odd

        # 7. Verschiedenes
        misc = data.get("Verschiedenes", {})
        if misc:
            html += '\n<div class="ITSg">Verschiedenes</div>\n'
            keys_misc = ["Zubehör im Lieferumfang", "Enthaltene Kabel", "Software inbegriffen", "Kennzeichnung", "Breite", "Tiefe"]
            for k in keys_misc:
                val = misc.get(k)
                if val:
                    html += self._row(k, val, odd)
                    odd = not odd

        html += '</div>'
        return html

    def generate_generic_html(self, data):
        """ Der Standard-Generator für alle anderen Kategorien """
        html = '<div class="ITSs">\n'
        
        has_groups = any(isinstance(v, dict) for v in data.values())
        if not has_groups: data = {"Allgemein": data}

        for group_name, fields in data.items():
            if group_name.startswith("_"): continue
            
            if isinstance(fields, dict):
                html += f'\n<div class="ITSg">{self._escape(group_name)}</div>\n'
                row_idx = 1
                for key, value in fields.items():
                    if key.startswith("_"): continue
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

        # --- INTELLIGENTE WEICHE 🛡️ ---
        is_ram = False
        is_case = False 
        is_gpu = False
        is_mb = False
        is_cpu = False

        # 1. RAM Check
        if "Speicher" in data:
            if "Formfaktor" in data.get("Speicher", {}):
                is_ram = True
        
        # 2. Case Check
        allgemein = data.get("Allgemein", {})
        if not is_ram:
            if "Max. Mainboard-Größe" in allgemein or "Systemgehäuse-Merkmale" in allgemein:
                is_case = True
        
        # 3. GPU Check
        if not is_ram and not is_case:
            if "Grafikprozessor" in allgemein or "CUDA-Kerne" in allgemein or "Streamprozessoren" in allgemein:
                is_gpu = True

        # 4. Mainboard Check
        if not is_ram and not is_case and not is_gpu:
            if "Chipsatz" in allgemein or "Prozessorsockel" in allgemein:
                is_mb = True
                
        # 5. CPU Erkennung: Wenn "Anz. der Kerne" oder "Taktfrequenz" im Prozessor-Block steht
        if not is_ram and not is_case and not is_gpu and not is_mb:
            if "Anz. der Kerne" in data.get("Prozessor", {}) or "Taktfrequenz" in data.get("Prozessor", {}):
                is_cpu = True        
        
        # Generator-Wahl (erweitern)
        if is_ram:
            technical_block = self._generate_ram_html(data)
        elif is_case:
            technical_block = self._generate_case_html(data)
        elif is_gpu:
            technical_block = self._generate_gpu_html(data)
        elif is_mb:
            technical_block = self._generate_mainboard_html(data)
        elif is_cpu:  
            technical_block = self._generate_cpu_html(data)
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