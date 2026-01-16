from .config import OPENAI_API_KEY, MODEL_NAME
from openai import OpenAI

# Client initialisieren
client = OpenAI(api_key=OPENAI_API_KEY)

# ==============================================================================
# 🚦 ROUTER KONFIGURATION
# ==============================================================================
ROUTER_RULES = [
    ("CPU-Kühler", ["cpu-kühler", "luftkühler", "wasserkühlung", "cpu cooler", "liquid cooler", "aio", "water cooling"]),
    ("Gehäuselüfter", ["gehäuselüfter", "case fan", "system fan", "lüfter", "fan"]),
    ("Mainboard", ["mainboard", "motherboard", "b650", "z790", "x670", "b760", "am5", "lga1700"]),
    ("Grafikkarte", ["grafikkarte", "gpu", "rtx", "radeon", "geforce", "gtx"]),
    ("Prozessor", ["prozessor", "cpu", "intel core", "amd ryzen"]),
    ("Arbeitsspeicher", ["arbeitsspeicher", "ddr4", "ddr5", "dimm", "so-dimm", "ram kit"]),
    ("Gehäuse", ["gehäuse", "midi tower", "big tower", "mini tower", "pc-case"]),
    ("Netzteil", ["netzteil", "power supply", "psu", "atx 3.0", "gold", "platinum"]),
    ("Speicher", ["ssd", "hdd", "festplatte", "m.2", "nvme", "sata"]),
    ("Monitor", ["monitor", "bildschirm", "display", "tft", "oled", "ips"]),
    ("Eingabegeräte", ["maus", "tastatur", "keyboard", "mouse", "keypad"]), # Hier landen die neuen
]

def classify_product_type(product_name, gtin):
    """
    Der 'Router': Entscheidet, was das Produkt ist.
    """
    name_lower = product_name.lower()
    
    # --- 🏎️ FAST LANE ---
    for category, keywords in ROUTER_RULES:
        for kw in keywords:
            if kw in name_lower:
                return category

    # --- 🧠 AI Router ---
    try:
        gtin_info = f"GTIN: {gtin}" if gtin else ""
        known_cats = [rule[0] for rule in ROUTER_RULES]
        cat_list_str = ", ".join(known_cats)
        
        response = client.chat.completions.create(
            model=MODEL_NAME, 
            messages=[
                {"role": "system", "content": f"Ordne den Artikel zu: [{cat_list_str}, Sonstiges]. Antworte NUR mit dem Wort."},
                {"role": "user", "content": f"Produkt: {product_name}\n{gtin_info}"}
            ],
            temperature=0.0
        )
        category = response.choices[0].message.content.strip()
        if ":" in category: category = category.split(":")[-1].strip()
        return category
    except Exception as e:
        print(f"   ⚠️ Router-Fehler: {e}")
        return "Sonstiges"

def get_prompt_by_category(product_name, gtin, forced_category=None):
    """ 
    Wählt den Prompt. 
    Wenn 'forced_category' gesetzt ist (durch Ordnerstruktur), wird der Router übersprungen.
    """
    
    if forced_category:
        category = forced_category
        # Kleines visuelles Feedback in der Konsole wäre hier gut, passiert aber in main.py
    else:
        category = classify_product_type(product_name, gtin)
    
    cat_lower = category.lower()

    # Basis-Prompt
    base_prompt = f"""
    Du bist ein technischer Hardware-Experte.
    Produkt: {product_name}
    GTIN: {gtin}
    
    Suche nach technischen Datenblättern.
    REGELN:
    1. Unauffindbar -> "N/A".
    2. Rate nicht.
    3. Einheiten PFLICHT (3.5 GHz).
    4. Trenner: "¦".
    5. Format: JSON only.
    6. Max 3-4 Suchen.
    """

    # === Dispatcher ===
    
    if "cpu-kühler" in cat_lower:
        return base_prompt + """
        Kategorie: CPU-Kühler
        ERSTELLE EIN HIERARCHISCHES JSON.
        WICHTIG: Unterscheide 'Luftkühler' vs 'AiO Wasserkühlung'.
        Benötigte JSON-Struktur:
        {
            "Allgemein": { "Gerätetyp": "Luftkühler oder AiO", "Modell": "Name", "TDP-Klasse": "Watt" },
            "Kompatibilität": { "Sockel": "AM4¦LGA1700..." },
            "Technische Daten": { "Bauhöhe (nur Kühler)": "mm", "Radiatorgröße": "mm", "Lüftergröße": "mm", "Lautstärke": "dBA" },
            "Beleuchtung & Features": { "Beleuchtung": "ARGB", "Anschluss": "PWM" }
        }
        """
        
    elif "kühler" in cat_lower and "cpu" not in cat_lower: # Speziell für WG 12 "Kühler"
        return base_prompt + """
        Kategorie: Kühler (CPU/Allgemein)
        ERSTELLE EIN HIERARCHISCHES JSON.
        
        WICHTIG:
        1. Identifiziere Sockel-Kompatibilität (z.B. AM4, LGA1700).
        2. Identifiziere die Bauhöhe in mm.
        3. Bestimme, ob für AMD, Intel oder beide.
        
        Benötigte JSON-Struktur:
        {
            "Allgemein": {
                "Gerätetyp": "Kühler",
                "Modell": "Name"
            },
            "Kompatibilität": {
                "Sockel": "Liste (z.B. AM4, AM5, LGA115x, LGA1200, LGA1700)"
            },
            "Technische Daten": {
                "Bauhöhe (nur Kühler)": "mm (Wichtig!)",
                "Lüftergröße": "mm"
            },
            "Verschiedenes": {
                "Besonderheiten": "Features"
            }
        }
        """    

    elif "gehäuselüfter" in cat_lower:
        return base_prompt + """
        Kategorie: Gehäuselüfter
        ERSTELLE EIN HIERARCHISCHES JSON.
        SPEZIAL: Wenn 'Neutral', leite Größe aus Namen ab, suche NICHT online.
        Benötigte JSON-Struktur:
        {
            "Allgemein": { "Gerätetyp": "Gehäuselüfter", "Modell": "Generic", "Farbe": "Schwarz", "Paketmenge": "1" },
            "Technische Daten": { "Lüfterdurchmesser": "mm", "Rotationsgeschwindigkeit": "rpm", "Lüfterhöhe": "mm", "Geräuschpegel": "dBA", "Lager": "Typ" },
            "Anschlüsse & Features": { "Stromanschluss": "PWM", "Beleuchtung": "ARGB" }
        }
        """

    elif "monitor" in cat_lower:
        return base_prompt + """
        Kategorie: Monitor
        ERSTELLE EIN HIERARCHISCHES JSON.
        Benötigte JSON-Struktur:
        {
            "Allgemein": { "Gerätetyp": "Monitor", "Modell": "Name", "Farbe": "Schwarz" },
            "Display": { "Diagonale": "Zoll", "Auflösung": "BxH", "Bildwiederholrate": "Hz", "Panel-Typ": "IPS/VA", "Helligkeit": "cd/m²" },
            "Schnittstellen": { "Anschlüsse": "Liste" },
            "Verschiedenes": { "Besonderheiten": "Sync, Pivot", "Zubehör": "Kabel" },
            "Energieversorgung": { "Stromverbrauch SDR (Eingeschaltet)": "kWh" }
        }
        """

    elif "netzteil" in cat_lower:
        return base_prompt + """
        Kategorie: Netzteil
        ERSTELLE EIN HIERARCHISCHES JSON.
        Benötigte JSON-Struktur:
        {
            "Allgemein": { "Gerätetyp": "Netzteil", "Netzteil-Formfaktor": "ATX" },
            "Stromversorgungsgerät": { "Leistungskapazität": "Watt", "80-PLUS-Zertifizierung": "Zertifikat", "Angaben zu Ausgangsleistungsanschlüssen": "Liste" },
            "Verschiedenes": { "Kühlsystem": "Lüfter" },
            "Abmessungen und Gewicht": { "Breite": "cm", "Tiefe": "cm", "Höhe": "cm" }
        }
        """

    elif "prozessor" in cat_lower:
        return base_prompt + """
        Kategorie: Prozessor
        ERSTELLE EIN HIERARCHISCHES JSON.
        Benötigte JSON-Struktur:
        {
            "Allgemein": { "Produkttyp": "Prozessor", "Serie": "Core i9", "Modell": "14900K" },
            "Prozessor": { "Sockel": "LGA1700", "Gesamtkerne": "24", "P-Cores (Anzahl)": "8" },
            "Speicher-Controller": { "Unterstützter Speichertyp": "DDR5" },
            "Integrierte Grafik": { "Typ": "UHD 770" }
        }
        """

    elif "grafikkarte" in cat_lower:
        return base_prompt + """
        Kategorie: Grafikkarte
        ERSTELLE EIN HIERARCHISCHES JSON.
        Benötigte JSON-Struktur:
        {
            "Allgemein": { "Gerätetyp": "Grafikkarten", "Chipsatz-Hersteller": "NVIDIA", "Grafikprozessor": "RTX 4070" },
            "Arbeitsspeicher": { "Grösse": "16 GB", "Technologie": "GDDR6" },
            "Systemanforderungen": { "Erforderliche Leistungsversorgung": "750 W", "Zusätzliche Anforderungen": "Stecker" },
            "Abmessungen und Gewicht": { "Breite": "mm", "Tiefe": "mm", "Höhe": "mm" }
        }
        """

    elif "mainboard" in cat_lower:
        return base_prompt + """
        Kategorie: Mainboard
        ERSTELLE EIN HIERARCHISCHES JSON.
        Benötigte JSON-Struktur:
        {
            "Allgemein": { "Produkttyp": "Motherboard", "Chipsatz": "B650", "Prozessorsockel": "AM5" },
            "Unterstützter RAM": { "Technologie": "DDR5", "Anzahl Steckplätze": "4" },
            "Erweiterung / Konnektivität": { "Schnittstellen (Intern)": "Liste", "Schnittstellen (Rückseite)": "Liste", "Speicherschnittstellen": "SATA/M.2" },
            "LAN": { "Netzwerkschnittstellen": "WiFi/LAN" }
        }
        """

    elif "arbeitsspeicher" in cat_lower or "ram" in cat_lower:
        return base_prompt + """
        Kategorie: RAM
        ERSTELLE EIN HIERARCHISCHES JSON.
        Benötigte JSON-Struktur:
        {
            "Allgemein": { "Kapazität": "32 GB" },
            "Arbeitsspeicher": { "Technologie": "DDR5", "Geschwindigkeit": "6000 MHz", "Latenzzeiten": "CL30" }
        }
        """

    elif "speicher" in cat_lower or "ssd" in cat_lower or "hdd" in cat_lower:
        return base_prompt + """
        Kategorie: Speicher (SSD/HDD)
        ERSTELLE EIN HIERARCHISCHES JSON.
        Benötigte JSON-Struktur:
        {
            "Allgemein": { "Gerätetyp": "SSD", "Kapazität": "1 TB", "Schnittstelle": "PCIe 4.0" },
            "Leistung": { "Interner Datendurchsatz (Lesen)": "MBps" }
        }
        """

    elif "gehäuse" in cat_lower:
        return base_prompt + """
        Kategorie: Gehäuse
        ERSTELLE EIN HIERARCHISCHES JSON.
        Benötigte JSON-Struktur:
        {
            "Allgemein": { "Formfaktor": "Midi Tower", "Max. Mainboard-Größe": "ATX" },
            "Kühlsystem (Installiert)": { "Lüfter (Vorne)": "Anzahl" },
            "Systemanforderungen": { "Max. Höhe CPU-Kühler": "mm", "Max. Länge Grafikkarte": "mm" },
            "Abmessungen und Gewicht": { "Breite": "mm", "Höhe": "mm", "Tiefe": "mm" }
        }
        """
        
    elif "eingabegeräte" in cat_lower or "tastatur" in cat_lower or "maus" in cat_lower or "keyboard" in cat_lower or "mouse" in cat_lower:
        return base_prompt + """
        Kategorie: Eingabegeräte (Maus, Tastatur, Sets)
        ERSTELLE EIN HIERARCHISCHES JSON.

        WICHTIG:
        1. Identifiziere den Typ: Maus, Tastatur, Desktop-Set, Keypad, etc.
        2. Verbindung: Kabelgebunden (USB) oder Kabellos (Funk/Bluetooth/Wireless).
        3. Layout: Falls Tastatur, welches Layout (DE/QWERTZ, US/QWERTY)?
        4. Farbe: Wichtig für den Namen.
        
        Benötigte JSON-Struktur:
        {
            "Allgemein": {
                "Gerätetyp": "z.B. Tastatur, Maus oder Desktop-Set",
                "Modell": "Name",
                "Farbe": "z.B. Schwarz"
            },
            "Konnektivität": {
                "Anschlusstechnik": "Verkabelt / Kabellos",
                "Schnittstelle": "z.B. USB, Bluetooth, 2.4 GHz"
            },
            "Technische Daten": {
                "Layout": "z.B. Deutsch (QWERTZ) oder N/A",
                "Tastenschalter": "z.B. Cherry MX Red (nur bei Tastatur)",
                "Bewegungsauflösung": "z.B. 16000 dpi (nur bei Maus)",
                "Anzahl Tasten": "Anzahl"
            },
            "Verschiedenes": {
                "Besonderheiten": "z.B. Beleuchtung (RGB), Ergonomisch"
            }
        }
        """   
        
    elif "kabel" in cat_lower or "adapter" in cat_lower or "cable" in cat_lower:
        return base_prompt + """
        Kategorie: Kabel & Adapter
        ERSTELLE EIN HIERARCHISCHES JSON.

        WICHTIG:
        1. Identifiziere die Anschlüsse GENAU (z.B. HDMI Stecker auf DVI Buchse).
        2. Identifiziere die Länge (falls Kabel).
        3. Identifiziere den Standard (z.B. Cat6, HDMI 2.1, USB 3.0).
        
        Benötigte JSON-Struktur:
        {
            "Allgemein": {
                "Gerätetyp": "Kabel oder Adapter",
                "Modell": "Name",
                "Farbe": "z.B. Schwarz"
            },
            "Technische Daten": {
                "Anschluss A": "z.B. HDMI (Stecker)",
                "Anschluss B": "z.B. DVI-D (Buchse)",
                "Länge": "z.B. 1.5 m (oder N/A bei Adaptern)",
                "Standard": "z.B. Cat6a, HDMI 2.1, USB 3.0"
            },
            "Verschiedenes": {
                "Besonderheiten": "z.B. Vergoldete Kontakte, Geschirmt"
            }
        }
        """ 
        
    elif "soundkarte" in cat_lower or "sound card" in cat_lower or "audio interface" in cat_lower:
        return base_prompt + """
        Kategorie: Soundkarte
        ERSTELLE EIN HIERARCHISCHES JSON.

        WICHTIG:
        1. Schnittstelle: Intern (PCIe/PCI) oder Extern (USB).
        2. Formfaktor: Prüfe explizit auf "Low Profile" (für schmale Gehäuse).
        3. Kanäle: 5.1, 7.1, Stereo.

        Benötigte JSON-Struktur:
        {
            "Allgemein": {
                "Gerätetyp": "Soundkarte (Intern/Extern)",
                "Modell": "Name",
                "Schnittstelle": "z.B. PCIe x1 oder USB 2.0"
            },
            "Audio": {
                "Soundmodus": "z.B. 5.1 Surround oder 7.1",
                "Auflösung": "z.B. 32-bit / 384 kHz",
                "Rauschabstand (SNR)": "z.B. 122 dB"
            },
            "Technische Daten": {
                "Low Profile": "Ja oder Nein (bzw. Low Profile Slotblech im Lieferumfang)",
                "Chipsatz": "z.B. Creative Sound Core3D"
            },
            "Anschlüsse": {
                "Eingänge": "Liste (Mikrofon, Line-In)",
                "Ausgänge": "Liste (Kopfhörer, Optisch/Toslink)"
            }
        }
        """   
    
    elif "audio" in cat_lower or "mikrofon" in cat_lower or "microphone" in cat_lower or "dac" in cat_lower or "interface" in cat_lower:
        return base_prompt + """
        Kategorie: Audio-Geräte (Mikrofone, Interfaces, DACs)
        ERSTELLE EIN HIERARCHISCHES JSON.

        WICHTIG:
        1. Identifiziere den Gerätetyp (z.B. Kondensator-Mikrofon, USB-Audio-Interface).
        2. Schnittstelle: USB, XLR, Klinke, PCIe?
        3. Features: Richtcharakteristik (bei Mikros), Auflösung (bei DACs).
        
        Benötigte JSON-Struktur:
        {
            "Allgemein": {
                "Gerätetyp": "z.B. Mikrofon oder Audio-Interface",
                "Modell": "Name",
                "Farbe": "z.B. Schwarz"
            },
            "Technische Daten": {
                "Schnittstelle": "z.B. USB-C, XLR, PCIe",
                "Low Profile": "Ja oder Nein (nur relevant bei internen Karten)",
                "Frequenzbereich": "z.B. 20 Hz - 20 kHz",
                "Richtcharakteristik": "z.B. Niere (nur bei Mikros)",
                "Auflösung": "z.B. 24-bit / 192 kHz"
            },
            "Anschlüsse": {
                "Eingänge": "Liste",
                "Ausgänge": "Liste"
            },
            "Verschiedenes": {
                "Besonderheiten": "z.B. Mute-Button, RGB, Inkl. Stativ"
            }
        }
        """
        
    elif "webcam" in cat_lower or "kamera" in cat_lower or "camera" in cat_lower:
        return base_prompt + """
        Kategorie: Webcam
        ERSTELLE EIN HIERARCHISCHES JSON.

        WICHTIG:
        1. Identifiziere die MAXIMALE Auflösung (z.B. 1080p, 4K UHD, 720p).
        2. Identifiziere die Framerate bei max. Auflösung (z.B. 30 fps, 60 fps).
        3. Identifiziere Anschluss (USB-A, USB-C) und Features (Mikrofon, Autofokus).
        
        Benötigte JSON-Struktur:
        {
            "Allgemein": {
                "Gerätetyp": "Webcam",
                "Modell": "Name",
                "Farbe": "z.B. Schwarz"
            },
            "Video": {
                "Max. Auflösung": "z.B. 1920 x 1080 (Full HD) oder 4K UHD",
                "Max. Bildrate": "z.B. 60 fps (oder 30 fps)",
                "Fokus-Einstellung": "z.B. Autofokus oder Fixfokus"
            },
            "Audio": {
                "Mikrofon integriert": "Ja / Nein",
                "Mikrofon-Typ": "z.B. Stereo oder Mono mit Rauschunterdrückung"
            },
            "Konnektivität": {
                "Schnittstelle": "z.B. USB 2.0 oder USB-C 3.0"
            },
            "Verschiedenes": {
                "Besonderheiten": "z.B. Privacy Cover, Stativgewinde, Ringlicht"
            }
        }
        """    
        
    elif "gamingstuhl" in cat_lower or "gaming chair" in cat_lower or "bürostuhl" in cat_lower:
        return base_prompt + """
        Kategorie: Gamingstuhl / Bürostuhl
        ERSTELLE EIN HIERARCHISCHES JSON.

        WICHTIG:
        1. Material: Stoff, Kunstleder (PU), Echtleder oder Mesh?
        2. Belastbarkeit: Max. Gewicht (z.B. 120 kg, 150 kg).
        3. Features: 4D-Armlehnen, Wippfunktion, Lendenwirbelstütze.
        
        Benötigte JSON-Struktur:
        {
            "Allgemein": {
                "Gerätetyp": "Gamingstuhl",
                "Modell": "Name",
                "Farbe": "z.B. Schwarz / Rot"
            },
            "Materialien": {
                "Bezug": "z.B. Stoff, PU-Kunstleder, Mesh",
                "Fußkreuz": "z.B. Aluminium oder Nylon"
            },
            "Technische Daten": {
                "Max. Belastbarkeit": "z.B. 150 kg",
                "Sitzbreite": "cm",
                "Rückenlehnenhöhe": "cm"
            },
            "Ausstattung": {
                "Armlehnen": "z.B. 4D verstellbar",
                "Funktionen": "Wippmechanik, Liegefunktion (180°)"
            }
        }
        """  
        
    elif "netzwerkkarte" in cat_lower or "network card" in cat_lower or "nic" in cat_lower:
        return base_prompt + """
        Kategorie: Netzwerkkarte (NIC)
        ERSTELLE EIN HIERARCHISCHES JSON.

        WICHTIG:
        1. Geschwindigkeit: z.B. 1 Gbit, 2.5 Gbit, 10 Gbit oder WiFi 6E/7.
        2. Schnittstelle: PCIe (Intern) oder USB (Extern).
        3. Formfaktor: Prüfe auf "Low Profile" (für Server/Mini-PCs).
        4. Anschlüsse: RJ45 (Kupfer), SFP+ (Glasfaser) oder Antennen (WLAN).

        Benötigte JSON-Struktur:
        {
            "Allgemein": {
                "Gerätetyp": "Netzwerkkarte",
                "Modell": "Name"
            },
            "Technische Daten": {
                "Übertragungsrate": "z.B. 10 Gbps oder 2400 Mbps (WiFi)",
                "Schnittstelle": "z.B. PCIe x4 oder USB 3.0",
                "Anschlusstyp": "z.B. 1x RJ45 oder 2x SFP+ oder WiFi",
                "Low Profile": "Ja oder Nein"
            },
            "Netzwerk": {
                "Standards": "z.B. IEEE 802.3an, WiFi 6 (802.11ax)",
                "Chipsatz": "z.B. Intel X550"
            }
        }
        """          
             
    #Fallback, neu Kategorien werden genau hier drüber eingefügt
    else:
        return base_prompt + """
        Identifiziere die Kategorie selbst.
        Erstelle ein sinnvolles, hierarchisches JSON.
        """