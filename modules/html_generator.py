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
        
        # NEU: Listen-Handling 🛠️
        # Wenn value eine echte Liste ist (z.B. ["OVP", "OCP"]), verbinden wir sie mit <br />
        if isinstance(value, list):
            # Bereinige jedes Element und verbinde
            cleaned_list = [self._escape(str(item)) for item in value]
            value_safe = " <br /> ".join(cleaned_list)
        else:
            # Standard-Handling für Text
            label_safe = self._escape(label)
            value_safe = self._escape(value)
            
            # SPEZIAL 1: " GB" durch "&nbsp;GB" ersetzen (RAM/Speicher)
            value_safe = value_safe.replace(" GB", "&nbsp;GB")
            
            # SPEZIAL 2: Trenner "¦" durch HTML-Umbruch ersetzen
            if "¦" in value_safe:
                value_safe = value_safe.replace("¦", " <br /> ")

        # Label immer escapen (wurde oben im else-Block gemacht, muss aber für beide Fälle gelten)
        label_safe = self._escape(label)
        
        css_class = "ITSr1" if is_odd else "ITSr0"
        
        return f'''
<div class="{css_class}">
<div class="ITSn">{label_safe}</div>

<div class="ITSv">{value_safe}</div>
</div>
'''
#RAMS
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
#Gehäuse
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
#GPU
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
#Mainboard
    def _generate_motherboard_html(self, data):
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
 #CPU   
    def _generate_cpu_html(self, data):
        """ Spezial-Generator für Prozessoren (CPUs) """
        html = '<div class="ITSs">\n'

        # 1. Allgemein
        html += '<div class="ITSg">Allgemein</div>\n'
        
        # Manuelle Abfrage der Allgemein-Werte für korrekte Reihenfolge
        gen = data.get("Allgemein", {})
        odd = True
        
        # Liste von (JSON-Key, HTML-Label)
        keys_gen = [
            ("Produkttyp", "Produkttyp"),
            ("Prozessorhersteller", "Hersteller"), # Optional
            ("Prozessorsockel", "Prozessorsockel"),
            ("Box", "Boxed") # Optional
        ]
        
        for k, label in keys_gen:
            val = gen.get(k)
            if val:
                html += self._row(label, val, odd)
                odd = not odd

        # 2. Prozessor Details (DER WICHTIGE TEIL)
        proc = data.get("Prozessor", {})
        if proc:
            html += '\n<div class="ITSg">Prozessor</div>\n'
            # Wir definieren exakt, welche Keys aus dem JSON wir wollen
            keys_proc = [
                ("Typ / Formfaktor", "Typ / Formfaktor"),
                ("Anz. der Kerne", "Anz. der Kerne"),
                ("Anz. der Threads", "Anz. der Threads"),
                ("Cache-Speicher", "Cache-Speicher"),
                ("Cache-Speicher-Details", "Cache-Speicher-Details"),
                ("Prozessoranz.", "Prozessoranz."),
                ("Taktfrequenz", "Taktfrequenz"),
                ("Max. Turbo-Taktfrequenz", "Max. Turbo-Taktfrequenz"),
                ("Geeignete Sockel", "Geeignete Sockel"), # Falls hier doppelt, egal
                ("Herstellungsprozess", "Herstellungsprozess"),
                ("Thermal Design Power (TDP)", "Thermal Design Power (TDP)"),
                ("Maximale Turbo-Leistung", "Maximale Turbo-Leistung"), # Neu!
                ("Temperaturspezifikationen", "Temperaturspezifikationen"),
                ("PCI Express Revision", "PCI Express Revision"),
                ("PCI Express-Konfigurationen", "PCI Express-Konfigurationen"),
                ("Anz. PCI Express Lanes", "Anz. PCI Express Lanes"),
                ("Architektur-Merkmale", "Architektur-Merkmale")
            ]
            
            for json_key, label in keys_proc:
                val = proc.get(json_key)
                if val:
                    html += self._row(label, val, odd)
                    odd = not odd

        # 3. Integrierte Grafik (Nur wenn vorhanden)
        gfx = data.get("Grafik", {}) # Achtung: Im JSON heißt der Block "Grafik", nicht "Integrierte Grafik"
        if not gfx: gfx = data.get("Integrierte Grafik", {}) # Fallback
        
        # Check: Ist da wirklich eine GPU?
        has_gfx = False
        gfx_val = gfx.get("Eingebaute Grafikadapter", "")
        if gfx_val and str(gfx_val).lower() in ["ja", "yes", "true", "1"]:
             has_gfx = True
        elif gfx.get("Typ"): # Fallback falls "Eingebaute Grafikadapter" fehlt
             has_gfx = True

        # Intel F-Serie Check (Sicherheitshalber)
        prod_name = data.get("_Produktname", "")
        if "F" in prod_name.split("-")[-1] and "KF" not in prod_name:
             has_gfx = False

        if has_gfx:
            html += '\n<div class="ITSg">Integrierte Grafik</div>\n'
            
            keys_gfx = [
                ("Typ", "Typ"), 
                ("On-Board Grafikadaptermodell", "Typ"), # JSON nutzt oft diesen langen Key
                ("Basisfrequenz", "Basisfrequenz"),
                ("On-Board Grafikadapter Basisfrequenz", "Basisfrequenz"),
                ("Maximale dynamische Frequenz der On-Board Grafikadapter", "Max. dynamische Frequenz")
            ]
            
            # Wir iterieren und vermeiden Duplikate (Typ vs On-Board Modell)
            seen_labels = set()
            for json_key, label in keys_gfx:
                if label in seen_labels: continue
                
                val = gfx.get(json_key)
                if val and str(val).lower() not in ["n/a", "nein", "no"]:
                    html += self._row(label, val, odd)
                    odd = not odd
                    seen_labels.add(label)

        # 4. Speicher Support
        mem = data.get("Speicher", {})
        if mem:
            html += '\n<div class="ITSg">Speicher-Support</div>\n'
            keys_mem = [
                ("Maximaler interner Speicher, vom Prozessor unterstützt", "Max. Größe"),
                ("Speichertaktraten, vom Prozessor unterstützt", "Speichertaktraten"),
                ("Speicherkanäle", "Speicherkanäle"),
                ("ECC", "ECC-Unterstützung")
            ]
            for json_key, label in keys_mem:
                val = mem.get(json_key)
                if val:
                    html += self._row(label, val, odd)
                    odd = not odd

        # 5. Verschiedenes & Architektur
        arch = data.get("Architektur-Merkmale", {})
        misc = data.get("Verschiedenes", {})
        
        # Wenn Architektur-Merkmale separat sind (im JSON oft so)
        arch_features = arch.get("Besonderheiten")
        if arch_features:
             # Wir packen das oft zu "Prozessor", aber hier ist es ein eigener Block im JSON
             # Packen wir es zu Verschiedenes oder ans Ende von Prozessor?
             # Deine Vorlage hat es im Prozessor-Block.
             pass # Schon oben in keys_proc abgedeckt? Nein, da ist es im JSON unter "Prozessor".
                  # Moment, im JSON ist es ein EIGENER Block "Architektur-Merkmale".
        
        # Korrektur: Architektur Merkmale explizit hinzufügen wenn noch nicht da
        if arch_features:
            html += '\n<div class="ITSg">Architektur</div>\n'
            html += self._row("Besonderheiten", arch_features, odd)
            odd = not odd

        if misc:
            html += '\n<div class="ITSg">Verschiedenes</div>\n'
            keys_misc = ["Verpackung", "Zubehör im Lieferumfang"]
            for k in keys_misc:
                val = misc.get(k)
                if val:
                    html += self._row(k, val, odd)
                    odd = not odd

        html += '</div>'
        return html
#Netzteile
    def _generate_psu_html(self, data):
        """ Spezial-Generator für Netzteile (PSU) """
        html = '<div class="ITSs">\n'

        # 1. Allgemein
        html += '<div class="ITSg">Allgemein</div>\n'
        gen = data.get("Allgemein", {})
        odd = True
        keys_gen = [
            ("Gerätetyp", "Gerätetyp"),
            ("Spezifikationseinhaltung", "Spezifikationseinhaltung"),
            ("Netzteil-Formfaktor", "Netzteil-Formfaktor"),
            ("Farbe", "Farbe"),
            ("Lokalisierung", "Lokalisierung")
        ]
        for k, label in keys_gen:
            val = gen.get(k)
            if val:
                html += self._row(label, val, odd)
                odd = not odd

        # 2. Stromversorgungsgerät (Der wichtigste Teil)
        power = data.get("Stromversorgungsgerät", {})
        if power:
            html += '\n<div class="ITSg">Stromversorgungsgerät</div>\n'
            # Feste Reihenfolge gemäß Vorlage
            keys_power = [
                ("Eingangsspannung", "Eingangsspannung"),
                ("Nötige Frequenz", "Nötige Frequenz"),
                ("Angaben zu Ausgangsleistungsanschlüssen", "Angaben zu Ausgangsleistungsanschlüssen"),
                ("Ausgangsspannung", "Ausgangsspannung"),
                ("Leistungskapazität", "Leistungskapazität"),
                ("Ausgangsstrom", "Ausgangsstrom"),
                ("Effizienz", "Effizienz"),
                ("Leistungsfaktor (LF)", "Leistungsfaktor (LF)"),
                ("Modulare Kabelverwaltung", "Modulare Kabelverwaltung"),
                ("80-PLUS-Zertifizierung", "80-PLUS-Zertifizierung")
            ]
            
            for k, label in keys_power:
                val = power.get(k)
                if val:
                    html += self._row(label, val, odd)
                    odd = not odd

        # 3. Verschiedenes
        misc = data.get("Verschiedenes", {})
        if misc:
            html += '\n<div class="ITSg">Verschiedenes</div>\n'
            keys_misc = [
                ("Enthaltene Kabel", "Enthaltene Kabel"),
                ("Zubehör im Lieferumfang", "Zubehör im Lieferumfang"),
                ("MTBF", "MTBF"),
                ("Kühlsystem", "Kühlsystem"),
                ("Besonderheiten", "Besonderheiten"),
                ("Kennzeichnung", "Kennzeichnung")
            ]
            for k, label in keys_misc:
                val = misc.get(k)
                if val:
                    html += self._row(label, val, odd)
                    odd = not odd

        # 4. Nachhaltigkeit (Optional)
        sust = data.get("Informationen zur Nachhaltigkeit", {})
        if sust:
             html += '\n<div class="ITSg">Informationen zur Nachhaltigkeit</div>\n'
             val = sust.get("ENERGY STAR")
             if val:
                 html += self._row("ENERGY STAR", val, odd)
                 odd = not odd

        # 5. Garantie
        warr = data.get("Herstellergarantie", {})
        if warr:
            html += '\n<div class="ITSg">Herstellergarantie</div>\n'
            html += self._row("Service und Support", warr.get("Service und Support"), True)

        # 6. Umgebungsbedingungen (Optional)
        env = data.get("Umgebungsbedingungen", {})
        if env:
            html += '\n<div class="ITSg">Umgebungsbedingungen</div>\n'
            html += self._row("Max. Betriebstemperatur", env.get("Max. Betriebstemperatur"), True)

        # 7. Abmessungen
        dims = data.get("Abmessungen und Gewicht", {})
        if dims:
            html += '\n<div class="ITSg">Abmessungen und Gewicht</div>\n'
            keys_dims = ["Breite", "Tiefe", "Höhe", "Gewicht"]
            for k in keys_dims:
                val = dims.get(k)
                if val:
                    html += self._row(k, val, odd)
                    odd = not odd

        html += '</div>'
        return html
#Wasserkühlung   
    def _generate_cooler_html(self, data):
        """ Spezial-Generator für CPU-Kühler """
        html = '<div class="ITSs">\n'

        # 1. Allgemein
        html += '<div class="ITSg">Allgemein</div>\n'
        gen = data.get("Allgemein", {})
        odd = True
        keys_gen = [
            ("Produkttyp", "Produkttyp"),
            ("Packungsinhalt", "Packungsinhalt"),
            ("Breite", "Breite"),
            ("Tiefe", "Tiefe"),
            ("Höhe", "Höhe"),
            ("Gewicht", "Gewicht"),
            ("Farbe", "Farbe"),
            ("Transportabmessungen (B x T x H)/Gewicht", "Transportabmessungen") # Falls vorhanden
        ]
        for k, label in keys_gen:
            val = gen.get(k)
            if val:
                html += self._row(label, val, odd)
                odd = not odd

        # 2. Kühlkörper und Lüfter (Das Herzstück)
        cool = data.get("Kühlkörper und Lüfter", {})
        if cool:
            html += '\n<div class="ITSg">Kühlkörper und Lüfter</div>\n'
            keys_cool = [
                ("Kompatibel mit", "Kompatibel mit"),
                ("Kühlermaterial", "Kühlermaterial"),
                ("Lüfterdurchmesser", "Lüfterdurchmesser"),
                ("Gebläsehöhe", "Gebläsehöhe"),
                ("Lüfterlager", "Lüfterlager"),
                ("Drehgeschwindigkeit", "Drehgeschwindigkeit"),
                ("Luftstrom", "Luftstrom"),
                ("Luftdruck", "Luftdruck"),
                ("Geräuschpegel", "Geräuschpegel"),
                ("Netzanschluss", "Netzanschluss"),
                ("Nennspannung", "Nennspannung"),
                ("Nennstrom", "Nennstrom"),
                ("Energieverbrauch", "Energieverbrauch"),
                ("Kabellänge", "Kabellänge"),
                ("Merkmale", "Merkmale")
            ]
            
            for k, label in keys_cool:
                val = cool.get(k)
                if val:
                    html += self._row(label, val, odd)
                    odd = not odd

        # 3. Verschiedenes
        misc = data.get("Verschiedenes", {})
        if misc:
            html += '\n<div class="ITSg">Verschiedenes</div>\n'
            keys_misc = [
                ("Montagekit", "Montagekit"),
                ("MTBF", "MTBF"),
                ("Kennzeichnung", "Kennzeichnung"),
                ("Besonderheiten", "Besonderheiten")
            ]
            for k, label in keys_misc:
                val = misc.get(k)
                if val:
                    html += self._row(label, val, odd)
                    odd = not odd

        # 4. Garantie
        warr = data.get("Herstellergarantie", {})
        if warr:
            html += '\n<div class="ITSg">Herstellergarantie</div>\n'
            html += self._row("Service und Support", warr.get("Service und Support"), True)

        html += '</div>'
        return html
    
    def _generate_monitor_html(self, data):
        """ Spezial-Generator für Monitore """
        html = '<div class="ITSs">\n'

        # 1. Allgemein
        html += '<div class="ITSg">Allgemein</div>\n'
        gen = data.get("Allgemein", {})
        odd = True
        
        keys_gen = [
            ("Gerätetyp", "Gerätetyp"),
            ("Energie Effizienzklasse", "Energie Effizienzklasse"),
            ("Energieklasse (HDR)", "Energieklasse (HDR)"),
            ("Diagonalabmessung", "Diagonalabmessung"),
            ("Geschwungener Bildschirm", "Geschwungener Bildschirm"),
            ("Panel-Typ", "Panel-Typ"),
            ("Seitenverhältnis", "Seitenverhältnis"),
            ("Native Auflösung", "Native Auflösung"),
            ("Helligkeit", "Helligkeit"),
            ("Kontrast", "Kontrast"),
            ("HDR-Zertifizierung", "HDR-Zertifizierung"),
            ("Reaktionszeit", "Reaktionszeit"),
            ("Farbunterstützung", "Farbunterstützung"),
            ("Farbe", "Farbe")
        ]
        
        for k, label in keys_gen:
            val = gen.get(k)
            if val:
                html += self._row(label, val, odd)
                odd = not odd

        # 2. Bildqualität
        qual = data.get("Bildqualität", {})
        if qual:
            html += '\n<div class="ITSg">Bildqualität</div>\n'
            keys_qual = [("Farbraum", "Farbraum"), ("Besonderheiten", "Besonderheiten")]
            for k, label in keys_qual:
                val = qual.get(k)
                if val:
                    html += self._row(label, val, odd)
                    odd = not odd

        # 3. Konnektivität
        conn = data.get("Konnektivität", {})
        if conn:
            html += '\n<div class="ITSg">Konnektivität</div>\n'
            html += self._row("Schnittstellen", conn.get("Schnittstellen"), odd)
            odd = not odd

        # 4. Mechanisch
        mech = data.get("Mechanisch", {})
        if mech:
            html += '\n<div class="ITSg">Mechanisch</div>\n'
            keys_mech = [
                ("Einstellungen der Anzeigeposition", "Einstellungen der Anzeigeposition"),
                ("Höheneinstellung", "Höheneinstellung"),
                ("Neigungswinkel", "Neigungswinkel"),
                ("VESA-Halterung", "VESA-Halterung")
            ]
            for k, label in keys_mech:
                val = mech.get(k)
                if val:
                    html += self._row(label, val, odd)
                    odd = not odd

        # 5. Stromversorgung
        power = data.get("Stromversorgung", {})
        if power:
            html += '\n<div class="ITSg">Stromversorgung</div>\n'
            keys_power = [
                ("Eingangsspannung", "Eingangsspannung"),
                ("Stromverbrauch SDR (eingeschaltet)", "Stromverbrauch SDR (eingeschaltet)"),
                ("Stromverbrauch HDR (eingeschaltet)", "Stromverbrauch HDR (eingeschaltet)")
            ]
            for k, label in keys_power:
                val = power.get(k)
                if val:
                    html += self._row(label, val, odd)
                    odd = not odd

        # 6. Abmessungen
        dims = data.get("Abmessungen und Gewicht", {})
        if dims:
            html += '\n<div class="ITSg">Abmessungen und Gewicht</div>\n'
            html += self._row("Details", dims.get("Details"), odd)
            odd = not odd

        # 7. Garantie
        warr = data.get("Herstellergarantie", {})
        if warr:
            html += '\n<div class="ITSg">Herstellergarantie</div>\n'
            html += self._row("Service und Support", warr.get("Service und Support"), True)

        html += '</div>'
        return html
    
#Festplatten HDD/SSD/NVMe    
    def _generate_storage_html(self, data):
        """ Spezial-Generator für Festplatten (SSD/HDD) """
        html = '<div class="ITSs">\n'

        # 1. Merkmale / Funktionen (Das wichtigste)
        # Wir prüfen beide Keys, da die KI manchmal variiert
        feats = data.get("Merkmale", data.get("Funktionen", {}))
        if feats:
            html += '<div class="ITSg">Merkmale</div>\n'
            odd = True
            keys_feats = [
                ("SSD-Formfaktor", "SSD-Formfaktor"),
                ("SSD Speicherkapazität", "SSD Speicherkapazität"), # SSD
                ("Festplattenkapazität", "Speicherkapazität"),      # HDD Fallback
                ("Schnittstelle", "Schnittstelle"),
                ("Speichertyp", "Speichertyp"),
                ("NVMe", "NVMe"),
                ("Komponente für", "Komponente für"),
                ("Hardwareverschlüsselung", "Hardwareverschlüsselung"), # Oft hier einsortiert
                ("Unterstützte Sicherheitsalgorithmen", "Unterstützte Sicherheitsalgorithmen"),
                ("Datenübertragungsrate", "Datenübertragungsrate"),
                ("Lesegeschwindigkeit", "Lesegeschwindigkeit"),
                ("Schreibgeschwindigkeit", "Schreibgeschwindigkeit"),
                ("DevSlp (Geräteschlaf)-Unterstützung", "DevSlp (Geräteschlaf)-Unterstützung"),
                ("S.M.A.R.T. Unterstützung", "S.M.A.R.T. Unterstützung"),
                ("TRIM-Unterstützung", "TRIM-Unterstützung"),
                ("Mittlere Betriebsdauer zwischen Ausfällen (MTBF)", "Mittlere Betriebsdauer zwischen Ausfällen (MTBF)"),
                ("TBW-Bewertung", "TBW-Bewertung")
            ]
            
            for json_key, label in keys_feats:
                val = feats.get(json_key)
                # Fallback: Manchmal packt die KI Sicherheit in einen eigenen Block, manchmal hier rein.
                if not val and json_key in ["Hardwareverschlüsselung", "Unterstützte Sicherheitsalgorithmen"]:
                    val = data.get("Sicherheit", {}).get(json_key)

                if val:
                    html += self._row(label, val, odd)
                    odd = not odd

        # 2. Sonstige Funktionen
        misc = data.get("Sonstige Funktionen", {})
        if misc:
             val = misc.get("Produktfarbe") or data.get("Allgemein", {}).get("Farbe")
             if val:
                 html += '\n<div class="ITSg">Sonstige Funktionen</div>\n'
                 html += self._row("Produktfarbe", val, True)

        # 3. Leistung / Energie
        perf = data.get("Leistung", data.get("Energie", {}))
        if perf:
            html += '\n<div class="ITSg">Leistung</div>\n'
            odd = True
            keys_perf = ["Stromverbrauch (max.)", "Stromverbrauch (durchschnittl.)", "Stromverbrauch (Leerlauf)"]
            for k in keys_perf:
                val = perf.get(k)
                if val:
                    html += self._row(k, val, odd)
                    odd = not odd

        # 4. Gewicht und Abmessungen
        dims = data.get("Gewicht und Abmessungen", data.get("Abmessungen und Gewicht", {}))
        if dims:
            html += '\n<div class="ITSg">Gewicht und Abmessungen</div>\n'
            odd = True
            keys_dims = ["Breite", "Tiefe", "Höhe", "Gewicht"]
            for k in keys_dims:
                val = dims.get(k)
                if val:
                    html += self._row(k, val, odd)
                    odd = not odd

        # 5. Betriebsbedingungen
        env = data.get("Betriebsbedingungen", {})
        if env:
            html += '\n<div class="ITSg">Betriebsbedingungen</div>\n'
            odd = True
            keys_env = ["Temperaturbereich in Betrieb", "Stoßfest (in Betrieb)"]
            for k in keys_env:
                val = env.get(k)
                if val:
                    html += self._row(k, val, odd)
                    odd = not odd

        # 6. Verpackung
        pack = data.get("Verpackungsdaten", data.get("Verpackungsinformation", {}))
        if pack:
            html += '\n<div class="ITSg">Verpackungsdaten</div>\n'
            keys_pack = ["Verpackungsart", "Betriebsanleitung"]
            for k in keys_pack:
                val = pack.get(k)
                if val:
                    html += self._row(k, val, odd)
                    odd = not odd

        html += '</div>'
        return html
 #Wasserkühlung AIO   
    def _generate_watercooling_html(self, data):
        """ Spezial-Generator für Wasserkühlungen (AiO) """
        html = '<div class="ITSs">\n'

        # 1. Allgemein
        html += '<div class="ITSg">Allgemein</div>\n'
        gen = data.get("Allgemein", {})
        odd = True
        
        keys_gen = [
            ("Produkttyp", "Produkttyp"),
            ("Packungsinhalt", "Packungsinhalt"),
            ("Breite", "Breite"),
            ("Tiefe", "Tiefe"),
            ("Höhe", "Höhe"),
            ("Gewicht", "Gewicht"),
            ("Farbe", "Farbe")
        ]
        for k, label in keys_gen:
            val = gen.get(k)
            if val:
                html += self._row(label, val, odd)
                odd = not odd

        # 2. Kühlkörper und Lüfter
        cool = data.get("Kühlkörper und Lüfter", {})
        if cool:
            html += '\n<div class="ITSg">Kühlkörper und Lüfter</div>\n'
            keys_cool = [
                ("Kompatibel mit", "Kompatibel mit"),
                ("Prozessorkompatibilität", "Prozessorkompatibilität"), # <--- WICHTIG
                ("Kühlermaterial", "Kühlermaterial"),
                ("Radiatormaterial", "Radiatormaterial"),
                ("Kühlerabmessungen", "Kühlerabmessungen"), # <--- WICHTIG
                ("Gebläseanzahl", "Gebläseanzahl"),         # <--- WICHTIG
                ("Lüfterdurchmesser", "Lüfterdurchmesser"),
                ("Gebläsehöhe", "Gebläsehöhe"),
                ("Lüfterlager", "Lüfterlager"),
                ("Drehgeschwindigkeit", "Drehgeschwindigkeit"),
                ("Luftstrom", "Luftstrom"),
                ("Luftdruck", "Luftdruck"),
                ("Geräuschpegel", "Geräuschpegel"),
                ("Netzanschluss", "Netzanschluss"),
                ("Merkmale", "Merkmale")
            ]
            
            for k, label in keys_cool:
                val = cool.get(k)
                if val:
                    html += self._row(label, val, odd)
                    odd = not odd

        # 3. Verschiedenes
        misc = data.get("Verschiedenes", {})
        if misc:
            html += '\n<div class="ITSg">Verschiedenes</div>\n'
            keys_misc = ["Montagekit", "Leistungsmerkmale", "Zubehör im Lieferumfang", "MTBF"]
            for k in keys_misc:
                val = misc.get(k)
                if val:
                    html += self._row(k, val, odd)
                    odd = not odd

        # 4. Garantie
        warr = data.get("Herstellergarantie", {})
        if warr:
            html += '\n<div class="ITSg">Herstellergarantie</div>\n'
            html += self._row("Service und Support", warr.get("Service und Support"), True)

        html += '</div>'
        return html

    def _generate_input_device_html(self, data):
        """ Spezial-Generator für Eingabegeräte (Robust & Sauber) """
        html = '<div class="ITSs">\n'

        # Hilfs-Variablen
        gen = data.get("Allgemein", {})
        tech = data.get("Technische Daten", {})
        conn = data.get("Konnektivität", {})
        inp = data.get("Eingabegerät", {})
        point = data.get("Zeigegerät", {})
        misc = data.get("Verschiedenes", {})

        # Helper zum Suchen von Werten über alle Blöcke hinweg
        def get_val(*keys):
            for k in keys:
                for source in [gen, conn, tech, inp, point, misc]:
                    if k in source and source[k] and str(source[k]).lower() not in ["n/a", "none", ""]:
                        return source[k]
            return None

        # 1. Allgemein (immer da)
        html += '<div class="ITSg">Allgemein</div>\n'
        odd = True
        html += self._row("Gerätetyp", get_val("Gerätetyp", "Typ"), odd); odd = not odd
        html += self._row("Schnittstelle", get_val("Schnittstelle", "Anschlusstechnik"), odd); odd = not odd
        html += self._row("Kabelloser Empfänger", get_val("Kabelloser Empfänger"), odd); odd = not odd
        html += self._row("Hintergrundbeleuchtung", get_val("Hintergrundbeleuchtung"), odd); odd = not odd
        html += self._row("Farbe", get_val("Farbe", "Produktfarbe"), odd); odd = not odd

        # 2. Eingabegerät (Tastatur) - Temporärer Buffer
        temp_html = ""
        # Wir sammeln Daten
        layout = get_val("Layout", "Lokalisierung und Layout", "Tastaturaufbau")
        switches = get_val("Tastenschalter", "Key Switch Typ", "Tastatur-Switch")
        tech_val = get_val("Tastaturtechnologie")
        ff = get_val("Formfaktor", "Tastatur Formfaktor")
        anti = get_val("Anti-Ghosting")
        
        # Zeilen bauen
        if layout: temp_html += self._row("Layout", layout, odd); odd = not odd
        if tech_val: temp_html += self._row("Technologie", tech_val, odd); odd = not odd
        if switches: temp_html += self._row("Schaltertyp", switches, odd); odd = not odd
        if ff: temp_html += self._row("Formfaktor", ff, odd); odd = not odd
        
        keys_count = get_val("Anzahl Tasten", "Tastenanzahl")
        if keys_count and str(keys_count).isdigit() and int(keys_count) > 20:
             temp_html += self._row("Anzahl Tasten", keys_count, odd); odd = not odd
        
        if anti: temp_html += self._row("Anti-Ghosting", anti, odd); odd = not odd
        
        # Nur hinzufügen, wenn Daten da sind
        if temp_html:
            html += '\n<div class="ITSg">Eingabegerät (Tastatur)</div>\n' + temp_html

        # 3. Zeigegerät (Maus) - Temporärer Buffer
        temp_html = ""
        sensor = get_val("Movement Detection Technologie", "Sensor", "Sensor-Technologie")
        dpi = get_val("Bewegungsauflösung", "Auflösung", "Auflösung (DPI)")
        perf = get_val("Leistung")
        align = get_val("Ausrichtung")

        if sensor: temp_html += self._row("Sensor-Technologie", sensor, odd); odd = not odd
        if dpi: temp_html += self._row("Auflösung (DPI)", dpi, odd); odd = not odd
        
        # Maus Tasten (< 20)
        keys_count = get_val("Anzahl Tasten", "Tastenanzahl")
        if keys_count and (not str(keys_count).isdigit() or int(keys_count) < 20):
             temp_html += self._row("Anzahl Tasten", keys_count, odd); odd = not odd

        if perf: temp_html += self._row("Leistung", perf, odd); odd = not odd
        if align: temp_html += self._row("Ausrichtung", align, odd); odd = not odd

        if temp_html:
            html += '\n<div class="ITSg">Zeigegerät (Maus)</div>\n' + temp_html

        # 4. Verschiedenes
        temp_html = ""
        specials = get_val("Besonderheiten")
        acc = get_val("Zubehör im Lieferumfang")
        cable = get_val("Kabellänge")
        soft = get_val("Software", "Software & Systemanforderungen")
        dims = get_val("Abmessungen (BxTxH)", "Abmessungen")
        weight = get_val("Gewicht") # Gewicht packen wir hierhin oder zu Allgemein

        if specials: temp_html += self._row("Besonderheiten", specials, odd); odd = not odd
        if acc: temp_html += self._row("Zubehör im Lieferumfang", acc, odd); odd = not odd
        if cable: temp_html += self._row("Kabellänge", cable, odd); odd = not odd
        if soft: temp_html += self._row("Software", soft, odd); odd = not odd
        if dims: temp_html += self._row("Abmessungen", dims, odd); odd = not odd
        if weight: temp_html += self._row("Gewicht", weight, odd); odd = not odd

        if temp_html:
            html += '\n<div class="ITSg">Verschiedenes</div>\n' + temp_html

        # 5. Garantie
        warr = data.get("Herstellergarantie", {})
        if warr:
            html += '\n<div class="ITSg">Herstellergarantie</div>\n'
            html += self._row("Service und Support", warr.get("Service und Support"), True)

        html += '</div>'
        return html
    
    def _generate_audio_html(self, data):
        """ Spezial-Generator für Audio (Robust für Headsets & Lautsprecher) """
        html = '<div class="ITSs">\n'

        # Hilfs-Variablen für alle möglichen Blöcke
        gen = data.get("Allgemein", {})
        audio_out = data.get("Audioausgang", {})
        tech = data.get("Technische Daten", {}) # Der "Rebell"-Block
        conn_block = data.get("Anschlüsse", {}) # Noch ein "Rebell"-Block
        mic = data.get("Mikrofon", {})
        speaker = data.get("Lautsprecher", {})
        power = data.get("Stromversorgung", {})
        misc = data.get("Verschiedenes", {})
        
        # Helper zum Suchen von Werten
        def get_val(*keys):
            for k in keys:
                for source in [gen, audio_out, tech, conn_block, mic, speaker, power, misc]:
                    if k in source and source[k] and str(source[k]).lower() not in ["n/a", "none", "", "nein"]:
                        return source[k]
            return None

        # 1. Allgemein
        html += '<div class="ITSg">Allgemein</div>\n'
        odd = True
        
        # Wir holen die wichtigsten Werte, egal wo sie stehen
        html += self._row("Produkttyp", get_val("Produkttyp", "Gerätetyp"), odd); odd = not odd
        html += self._row("Formfaktor", get_val("Kopfhörer-Formfaktor", "Formfaktor", "Bauform"), odd); odd = not odd
        html += self._row("Lautsprechertyp", get_val("Lautsprechertyp"), odd); odd = not odd
        html += self._row("Verwendung", get_val("Empfohlene Verwendung"), odd); odd = not odd
        html += self._row("Farbe", get_val("Farbe"), odd); odd = not odd
        html += self._row("Gewicht", get_val("Gewicht"), odd); odd = not odd

        # 2. Audio-Specs (Headset & Boxen gemischt)
        # Wir sammeln alles in einem Buffer
        temp_html = ""
        
        mode = get_val("Soundmodus", "Audio Kanäle")
        freq = get_val("Frequenzgang", "Frequenzbereich")
        imp = get_val("Impedanz")
        sens = get_val("Empfindlichkeit")
        driver = get_val("Membran", "Treibergröße")
        rms = get_val("RMS-Leistung", "Leistung") # Bei Lautsprechern oft in Leistung
        
        if mode: temp_html += self._row("Soundmodus", mode, odd); odd = not odd
        if freq: temp_html += self._row("Frequenzgang", freq, odd); odd = not odd
        if imp: temp_html += self._row("Impedanz", imp, odd); odd = not odd
        if sens: temp_html += self._row("Empfindlichkeit", sens, odd); odd = not odd
        if driver: temp_html += self._row("Treibergröße", driver, odd); odd = not odd
        if rms: temp_html += self._row("Leistung (RMS)", rms, odd); odd = not odd

        if temp_html:
            html += '\n<div class="ITSg">Audio-Spezifikationen</div>\n' + temp_html

        # 3. Mikrofon (Nur wenn vorhanden)
        mic_type = get_val("Typ", "Richtcharakteristik")
        # Check ob es nach Mikrofon aussieht
        if mic_type or "mikrofon" in str(data).lower():
            temp_html = ""
            if mic_type: temp_html += self._row("Mikrofon-Typ", mic_type, odd); odd = not odd
            
            # Manchmal sind Mikrofon-Frequenzen separat gelistet, oft aber schwer zu trennen.
            # Wir verlassen uns hier auf explizite Mikrofon-Blöcke wenn möglich.
            mic_freq = mic.get("Frequenzgang")
            if mic_freq: temp_html += self._row("Frequenzgang (Mikro)", mic_freq, odd); odd = not odd
            
            if temp_html:
                html += '\n<div class="ITSg">Mikrofon</div>\n' + temp_html

        # 4. Verbindungen & Strom
        temp_html = ""
        conn_tech = get_val("Anschlusstechnik", "Schnittstelle", "Verbindung")
        wireless = get_val("Drahtlose Technologie", "Bluetooth-Version")
        battery = get_val("Batterie", "Akku")
        runtime = get_val("Betriebszeit (bis zu)", "Akkulaufzeit")
        
        if conn_tech: temp_html += self._row("Anschlusstechnik", conn_tech, odd); odd = not odd
        if wireless: temp_html += self._row("Wireless-Tech", wireless, odd); odd = not odd
        if battery: temp_html += self._row("Batterie", battery, odd); odd = not odd
        if runtime: temp_html += self._row("Akkulaufzeit", runtime, odd); odd = not odd
        
        if temp_html:
            html += '\n<div class="ITSg">Verbindungen & Energie</div>\n' + temp_html

        # 5. Verschiedenes
        temp_html = ""
        feat = get_val("Besonderheiten", "Zusätzliche Funktionen")
        acc = get_val("Zubehör im Lieferumfang")
        
        if feat: temp_html += self._row("Besonderheiten", feat, odd); odd = not odd
        if acc: temp_html += self._row("Zubehör", acc, odd); odd = not odd

        if temp_html:
            html += '\n<div class="ITSg">Verschiedenes</div>\n' + temp_html

        # 6. Garantie
        warr = data.get("Herstellergarantie", {})
        val = warr.get("Service und Support")
        if val:
            html += '\n<div class="ITSg">Herstellergarantie</div>\n'
            html += self._row("Service und Support", val, True)

        html += '</div>'
        return html
    
    def _generate_usb_stick_html(self, data):
        """ Spezial-Generator für USB-Sticks (Nach Shop-Schablone) """
        html = '<div class="ITSs">\n'

        # 1. Leistungen (Das Herzstück)
        perf = data.get("Leistungen", data.get("Speicher", {}))
        if perf:
            html += '<div class="ITSg">Leistungen</div>\n'
            odd = True
            keys_perf = [
                ("Kapazität", "Kapazität"),
                ("Geräteschnittstelle", "Geräteschnittstelle"),
                ("USB-Version", "USB-Version"),
                ("Lesegeschwindigkeit", "Lesegeschwindigkeit"),
                ("Schreibgeschwindigkeit", "Schreibgeschwindigkeit"),
                ("Kompatible Betriebssysteme", "Kompatible Betriebssysteme")
            ]
            for k, label in keys_perf:
                val = perf.get(k)
                if val:
                    html += self._row(label, val, odd)
                    odd = not odd

        # 2. Design
        design = data.get("Design", data.get("Allgemein", {}))
        if design:
            html += '\n<div class="ITSg">Design</div>\n'
            # Reset odd/even optional, hier machen wir weiter
            keys_design = [
                ("Formfaktor", "Formfaktor"),
                ("Produktfarbe", "Produktfarbe"),
                ("Schlüsselanhänger", "Schlüsselanhänger")
            ]
            for k, label in keys_design:
                val = design.get(k)
                if val:
                    html += self._row(label, val, odd)
                    odd = not odd

        # 3. Lieferumfang
        box = data.get("Lieferumfang", {})
        if box:
            val = box.get("Menge pro Packung")
            if val:
                html += '\n<div class="ITSg">Lieferumfang</div>\n'
                html += self._row("Menge pro Packung", val, odd); odd = not odd

        # 4. Gewicht und Abmessungen
        dims = data.get("Gewicht und Abmessungen", data.get("Abmessungen und Gewicht", {}))
        if dims:
            html += '\n<div class="ITSg">Gewicht und Abmessungen</div>\n'
            keys_dims = ["Breite", "Tiefe", "Höhe", "Gewicht"]
            for k in keys_dims:
                val = dims.get(k)
                if val:
                    html += self._row(k, val, odd)
                    odd = not odd

        # 5. Technische Details / Betriebsbedingungen
        tech = data.get("Technische Details", {})
        env = data.get("Betriebsbedingungen", {})
        
        # Falls Technische Details da sind (HS Code)
        if tech:
             val = tech.get("Warentarifnummer (HS)")
             if val:
                 html += '\n<div class="ITSg">Technische Details</div>\n'
                 html += self._row("Warentarifnummer (HS)", val, odd); odd = not odd

        if env:
            html += '\n<div class="ITSg">Betriebsbedingungen</div>\n'
            keys_env = ["Betriebstemperatur", "Temperaturbereich bei Lagerung"]
            for k in keys_env:
                val = env.get(k)
                if val:
                    html += self._row(k, val, odd)
                    odd = not odd

        # 6. Garantie
        warr = data.get("Herstellergarantie", {})
        if warr:
            html += '\n<div class="ITSg">Herstellergarantie</div>\n'
            html += self._row("Service und Support", warr.get("Service und Support"), True)

        html += '</div>'
        return html
    
    def _generate_network_html(self, data):
        """ Spezial-Generator für Netzwerkadapter (WLAN / LAN) """
        html = '<div class="ITSs">\n'

        # 1. Allgemein
        html += '<div class="ITSg">Allgemein</div>\n'
        gen = data.get("Allgemein", {})
        odd = True
        keys_gen = [
            ("Gerätetyp", "Gerätetyp"),
            ("Formfaktor", "Formfaktor"),
            ("Schnittstellentyp", "Schnittstellentyp (Bustyp)"),
            ("Farbe", "Produktfarbe")
        ]
        for k, label in keys_gen:
            val = gen.get(k)
            if val:
                html += self._row(label, val, odd)
                odd = not odd

        # 2. Anschlüsse und Schnittstellen (Aus Schablone 2)
        conn_if = data.get("Anschlüsse und Schnittstellen", {})
        if conn_if:
            html += '\n<div class="ITSg">Anschlüsse und Schnittstellen</div>\n'
            keys_conn = [
                ("Anzahl Ethernet-LAN-Anschlüsse (RJ-45)", "Anzahl Ethernet-LAN-Anschlüsse (RJ-45)"),
                ("Hostschnittstelle", "Hostschnittstelle"),
                ("Schnittstelle", "Schnittstelle"),
                ("Übertragungstechnik", "Übertragungstechnik")
            ]
            for k, label in keys_conn:
                val = conn_if.get(k)
                if val:
                    html += self._row(label, val, odd)
                    odd = not odd

        # 3. Netzwerk (Das Herzstück)
        net = data.get("Netzwerk", {})
        if net:
            html += '\n<div class="ITSg">Netzwerk</div>\n'
            keys_net = [
                ("Anschlusstechnik", "Anschlusstechnik"),
                ("Netzstandard", "Netzstandard"),
                ("Data Link Protocol", "Data Link Protocol"),
                ("Datenübertragungsrate", "Datenübertragungsrate"),
                ("Maximale Datenübertragungsrate", "Maximale Datenübertragungsrate"),
                ("Ethernet LAN Datentransferraten", "Ethernet LAN Datentransferraten"),
                ("Verkabelungstechnologie", "Verkabelungstechnologie"),
                ("Frequenzband", "Frequenzband"), # WLAN
                ("Vollduplex", "Vollduplex"),
                ("Jumbo Frames Unterstützung", "Jumbo Frames Unterstützung"),
                ("Wake-on-LAN bereit", "Wake-on-LAN bereit"),
                ("Leistungsmerkmale", "Leistungsmerkmale"),
                ("Statusanzeiger", "Statusanzeiger"),
                ("Produktzertifizierungen", "Produktzertifizierungen")
            ]
            for k, label in keys_net:
                val = net.get(k)
                if val:
                    html += self._row(label, val, odd)
                    odd = not odd

        # 4. Antenne (WLAN)
        ant = data.get("Antenne", {})
        if ant:
            val1 = ant.get("Antenne")
            val2 = ant.get("Antennenanzahl")
            if val1 or val2:
                html += '\n<div class="ITSg">Antenne</div>\n'
                if val1: html += self._row("Typ", val1, odd); odd = not odd
                if val2: html += self._row("Anzahl", val2, odd); odd = not odd

        # 5. Erweiterung / Konnektivität (Aus Schablone 1)
        ext = data.get("Erweiterung/Konnektivität", data.get("Erweiterung / Konnektivität", {}))
        if ext:
             html += '\n<div class="ITSg">Erweiterung/Konnektivität</div>\n'
             keys_ext = [("Schnittstellen", "Schnittstellen")]
             for k, label in keys_ext:
                 val = ext.get(k)
                 if val: html += self._row(label, val, odd); odd = not odd

        # 6. Systemanforderung
        sys = data.get("Systemanforderung", data.get("Software / Systemanforderungen", {}))
        if sys:
             html += '\n<div class="ITSg">Systemanforderung</div>\n'
             keys_sys = [("Erforderliches Betriebssystem", "Erforderliches Betriebssystem"), 
                         ("Unterstützte Linux-Betriebssysteme", "Unterstützte Linux-Betriebssysteme"),
                         ("Unterstützt Windows-Betriebssysteme", "Unterstützt Windows-Betriebssysteme")]
             for k, label in keys_sys:
                 val = sys.get(k)
                 if val: html += self._row(label, val, odd); odd = not odd

        # 7. Betriebsbedingungen
        env = data.get("Betriebsbedingungen", data.get("Umgebungsbedingungen", {}))
        if env:
            html += '\n<div class="ITSg">Betriebsbedingungen</div>\n'
            keys_env = ["Temperaturbereich in Betrieb", "Temperaturbereich bei Lagerung", "Min Betriebstemperatur", "Max. Betriebstemperatur", "Luftfeuchtigkeit in Betrieb"]
            for k, label in keys_env:
                val = env.get(k)
                if val:
                    html += self._row(k, val, odd)
                    odd = not odd

        # 8. Garantie
        warr = data.get("Herstellergarantie", {})
        if warr:
            html += '\n<div class="ITSg">Herstellergarantie</div>\n'
            html += self._row("Service und Support", warr.get("Service und Support"), True)

        html += '</div>'
        return html
    
    def _generate_mousepad_html(self, data):
        """ Spezial-Generator für Mauspads """
        html = '<div class="ITSs">\n'
        
        # Allgemein
        html += '<div class="ITSg">Allgemein</div>\n'
        gen = data.get("Allgemein", {})
        odd = True
        keys_gen = [("Gerätetyp", "Gerätetyp"), ("Produktmaterial", "Material"), ("Farbe", "Farbe"), 
                    ("Breite", "Breite"), ("Tiefe", "Tiefe"), ("Höhe", "Dicke")]
        for k, label in keys_gen:
            val = gen.get(k)
            if val: html += self._row(label, val, odd); odd = not odd

        # Verschiedenes
        misc = data.get("Verschiedenes", {})
        if misc:
            html += '\n<div class="ITSg">Verschiedenes</div>\n'
            keys_misc = [("Besonderheiten", "Besonderheiten"), ("Größenklasse", "Größe")]
            for k, label in keys_misc:
                val = misc.get(k)
                if val: html += self._row(label, val, odd); odd = not odd
        
        html += '</div>'
        return html

    def _generate_service_html(self, data):
        """ Spezial-Generator für Services """
        html = '<div class="ITSs">\n'

        # Allgemein
        html += '<div class="ITSg">Allgemein</div>\n'
        gen = data.get("Allgemein", {})
        odd = True
        keys_gen = [("Produkttyp", "Typ"), ("Dienstleistungstyp", "Leistung"), ("Lokalisierung", "Region")]
        for k, label in keys_gen:
             val = gen.get(k)
             if val: html += self._row(label, val, odd); odd = not odd

        # Details
        det = data.get("Details", {})
        if det:
            html += '\n<div class="ITSg">Details</div>\n'
            keys_det = [("Service inbegriffen", "Inklusive"), ("Volle Vertragslaufzeit", "Laufzeit"), 
                        ("Reaktionszeit", "Reaktionszeit"), ("Serviceverfügbarkeit", "Verfügbarkeit")]
            for k, label in keys_det:
                val = det.get(k)
                if val: html += self._row(label, val, odd); odd = not odd
        
        html += '</div>'
        return html
    
    def _generate_software_html(self, data):
        """ Generiert HTML speziell für Software/Lizenzen """
        html = '<div class="ITSs">\n'
        
        # Diese Kategorien wollen wir in dieser Reihenfolge ausgeben
        target_sections = [
            "Allgemein", 
            "Lizenzierung", 
            "Systemanforderungen", 
            "Kompatibilität", 
            "Verschiedenes"
        ]

        row_toggle = True # Für das abwechselnde Farbschema (ITSr1 / ITSr0)

        for section in target_sections:
            if section in data and isinstance(data[section], dict):
                # Kategorie-Header (z.B. "Systemanforderungen")
                html += f'<div class="ITSg">{section}</div>\n'
                
                for key, value in data[section].items():
                    # Leere Werte überspringen
                    if not value or str(value).lower() in ["n/a", "none"]:
                        continue

                    row_class = "ITSr1" if row_toggle else "ITSr0"
                    
                    html += f'<div class="{row_class}">\n'
                    html += f'<div class="ITSn">{key}</div>\n'
                    html += f'<div class="ITSv">{value}</div>\n'
                    html += '</div>\n'
                    
                    row_toggle = not row_toggle # Umschalten für nächste Zeile

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
        is_psu = False
        is_cooler = False
        is_monitor = False
        is_storage = False
        is_water = False
        is_input = False
        is_audio = False
        is_usb_stick = False
        is_network = False
        is_mousepad = False
        is_service = False
        is_software = False

        allgemein = data.get("Allgemein", {})

        # 1. RAM Check
        if "Speicher" in data:
            if "Formfaktor" in data.get("Speicher", {}):
                is_ram = True
        
        # 2. Case Check
        if not is_ram:
            if "Max. Mainboard-Größe" in allgemein or "Systemgehäuse-Merkmale" in allgemein:
                is_case = True
        
        # 3. GPU Check
        if not is_ram and not is_case:
            if "Grafikprozessor" in allgemein or "CUDA-Kerne" in allgemein or "Streamprozessoren" in allgemein:
                is_gpu = True

        # 4. CPU Check (JETZT VOR MAINBOARD!)
        # Wir prüfen auf Kerne/Takt im Prozessor-Block -> Das hat KEIN Mainboard
        if not is_ram and not is_case and not is_gpu:
            if "Anz. der Kerne" in data.get("Prozessor", {}) or "Taktfrequenz" in data.get("Prozessor", {}):
                is_cpu = True

        # 5. Mainboard Check (NACH CPU)
        if not is_ram and not is_case and not is_gpu and not is_cpu:
            if "Chipsatz" in allgemein or "Prozessorsockel" in allgemein:
                is_mb = True
                
        # 6. PSU Check
        if not is_ram and not is_case and not is_gpu and not is_mb and not is_cpu:
             # Prüfen auf typische Netzteil-Schlüsselwörter
             power_block = data.get("Stromversorgungsgerät", {})
             if "Leistungskapazität" in power_block or "80-PLUS-Zertifizierung" in power_block:
                 is_psu = True
                 
        # 7. Cooler Check
        if not is_ram and not is_case and not is_gpu and not is_mb and not is_cpu and not is_psu:
             # Wir suchen nach dem spezifischen Block aus dem Prompt
             if "Kühlkörper und Lüfter" in data:
                 is_cooler = True  
                 
        # 8. Monitor Check
        if not is_ram and not is_case and not is_gpu and not is_mb and not is_cpu and not is_psu and not is_cooler:
             # Prüfe auf typische Monitor-Keys
             if "Diagonalabmessung" in allgemein or "Native Auflösung" in allgemein:
                 is_monitor = True   
                 
        # 9. Storage Check
        if not is_ram and not is_case and not is_gpu and not is_mb and not is_cpu and not is_psu and not is_cooler and not is_monitor:
             # Prüfe auf typische Speicher-Keys in "Merkmale" oder "Allgemein"
             merkmale = data.get("Merkmale", {})
             if "SSD Speicherkapazität" in merkmale or "Festplattenkapazität" in merkmale or "TBW-Bewertung" in merkmale:
                 is_storage = True
             # Fallback für einfache HDDs
             if "U/min" in str(merkmale) and "Cache" in str(merkmale): # Typisch HDD
                 is_storage = True  
        
        # 10. Watercooling Check
        if not is_ram and not is_case and not is_gpu and not is_mb and not is_cpu and not is_psu and not is_cooler and not is_monitor and not is_storage:
             if "Radiator-Abmessungen" in data.get("Kühlkörper und Lüfter", {}) or "Radiator" in str(data):
                 is_water = True
             # Fallback: Wenn "Wasserkühlung" im Titel steht
             prod_name_lower = data.get("_Produktname", "").lower()
             if "wasser" in prod_name_lower or "liquid" in prod_name_lower or "aio" in prod_name_lower:
                 is_water = True   
                 
        # 11. Input Device Check
        if not is_ram and not is_case and not is_gpu and not is_mb and not is_cpu and not is_psu and not is_cooler and not is_monitor and not is_storage and not is_water:
             
             # Helper function to check if a key exists in ANY dictionary in data
             def key_exists(key, d):
                 if isinstance(d, dict):
                     if key in d: return True
                     for v in d.values():
                         if isinstance(v, dict) and key_exists(key, v): return True
                 return False

             # Aggressive Prüfung auf Eingabe-Features, egal wo sie stehen
             if key_exists("Bewegungsauflösung", data) or key_exists("Tastaturtechnologie", data) or key_exists("Tastenschalter", data):
                 is_input = True
             
             # Fallback Name
             prod_name_lower = data.get("_Produktname", "").lower()
             if "tastatur" in prod_name_lower or "keyboard" in prod_name_lower or "maus" in prod_name_lower or "mouse" in prod_name_lower:
                 is_input = True 
                 
        # 12. Audio Check (Aggressiv)
        if not is_ram and not is_case and not is_gpu and not is_mb and not is_cpu and not is_psu and not is_cooler and not is_monitor and not is_storage and not is_water and not is_input:
             # Suche nach Audio-Begriffen im ganzen JSON
             def has_audio_key(d):
                 keys = ["Frequenzbereich", "Soundmodus", "Richtcharakteristik", "Lautsprecher", "Headset"]
                 for k in keys:
                     if k in str(d): return True
                 return False

             if has_audio_key(data) or "Audioausgang" in data:
                 is_audio = True
             
             # Fallback Name
             prod_name_lower = data.get("_Produktname", "").lower()
             if "headset" in prod_name_lower or "kopfhörer" in prod_name_lower or "lautsprecher" in prod_name_lower or "soundbar" in prod_name_lower or "speaker" in prod_name_lower:
                 is_audio = True  
                 
        # 13. USB-Stick Check
        if not is_ram and not is_case and not is_gpu and not is_mb and not is_cpu and not is_psu and not is_cooler and not is_monitor and not is_storage and not is_water and not is_input and not is_audio:
             # Check auf typische USB-Stick Keys
             if "Lesegeschwindigkeit" in data.get("Speicher", {}) and "Schnittstellentyp" in data.get("Speicher", {}):
                 is_usb_stick = True
             
             # Name Check (Vorsicht vor WLAN-Sticks! Wir schließen sie aus)
             name = data.get("_Produktname", "").lower()
             if ("usb" in name and ("stick" in name or "drive" in name or "speicher" in name or "pen" in name)) and "wlan" not in name and "wifi" not in name and "bluetooth" not in name:
                 is_usb_stick = True 
                 
        # 14. Network Check
        if not is_ram and not is_case and not is_gpu and not is_mb and not is_cpu and not is_psu and not is_cooler and not is_monitor and not is_storage and not is_water and not is_input and not is_audio and not is_usb_stick:
             # Check auf Netzwerk-Keys
             if "Data Link Protocol" in data.get("Netzwerk", {}) or "Frequenzband" in data.get("Netzwerk", {}):
                 is_network = True
             
             # Name Check
             name = data.get("_Produktname", "").lower()
             if "wlan" in name or "wifi" in name or "bluetooth" in name or "netzwerk" in name or "network" in name or "adapter" in name or "pci express" in name:
                 is_network = True  
        
        # 15. Software Check
        if not is_ram and not is_case and not is_gpu and not is_mb and not is_cpu and not is_psu and not is_cooler and not is_monitor and not is_storage and not is_water and not is_input and not is_audio and not is_usb_stick and not is_network:
             # Check auf Software-Keys
             if "Lizenztyp" in data.get("Lizenzierung", {}) or "Plattform" in data.get("Allgemein", {}):
                 is_software = True
             
             # Name Check
             name = data.get("_Produktname", "").lower()
             if "windows" in name or "office" in name or "kaspersky" in name or "norton" in name or "adobe" in name or "software" in name or "spiel" in name or "game" in name:
                 is_software = True
        
        # 16. Mauspad Check
        if not is_ram and not is_case and not is_gpu and not is_mb and not is_cpu and not is_psu and not is_cooler and not is_monitor and not is_storage and not is_water and not is_input and not is_audio and not is_usb_stick and not is_network and not is_software:
             name = data.get("_Produktname", "").lower()
             if "mauspad" in name or "mousepad" in name or "deskmat" in name:
                 is_mousepad = True

        # 17. Service Check
        # Hier wird 'is_mousepad' verwendet, deshalb muss Block 16 zwingend davor stehen!
        if not is_ram and not is_case and not is_gpu and not is_mb and not is_cpu and not is_psu and not is_cooler and not is_monitor and not is_storage and not is_water and not is_input and not is_audio and not is_usb_stick and not is_network and not is_software and not is_mousepad:
             name = data.get("_Produktname", "").lower()
             if "service" in name or "garantie" in name or "warranty" in name or "care" in name or "support" in name or "installation" in name or "bearbeitung" in name:
                 is_service = True
        
        # Generator-Wahl (FINALER BLOCK)
        if is_mb:
            technical_block = self._generate_motherboard_html(data)
        elif is_cpu:
            technical_block = self._generate_cpu_html(data)
        elif is_gpu:
            technical_block = self._generate_gpu_html(data)
        elif is_ram:
            technical_block = self._generate_ram_html(data)
        elif is_case:
            technical_block = self._generate_case_html(data)
        elif is_psu:
            technical_block = self._generate_psu_html(data)
        elif is_cooler:
            technical_block = self._generate_cooler_html(data)
        elif is_monitor:
            technical_block = self._generate_monitor_html(data)
        elif is_storage:
            technical_block = self._generate_storage_html(data)
        elif is_water:
            technical_block = self._generate_watercooling_html(data)
        elif is_input:
            technical_block = self._generate_input_device_html(data)
        elif is_audio:
            technical_block = self._generate_audio_html(data)
        elif is_usb_stick:
            technical_block = self._generate_usb_stick_html(data)
        elif is_network:
            technical_block = self._generate_network_html(data)
        elif is_software:
            technical_block = self._generate_software_html(data)
        elif is_mousepad:
            technical_block = self._generate_mousepad_html(data)
        elif is_service:
            technical_block = self._generate_service_html(data)
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