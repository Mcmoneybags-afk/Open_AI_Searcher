from .config import OPENAI_API_KEY, MODEL_NAME
from openai import OpenAI

# Client initialisieren
client = OpenAI(api_key=OPENAI_API_KEY)

# ==============================================================================
# 🚦 ROUTER KONFIGURATION (Hier neue Kategorien hinzufügen!)
# ==============================================================================
# Die Reihenfolge ist WICHTIG! Spezifische Begriffe müssen VOR generischen stehen.
# Struktur: ("Kategorie-Name", [Liste der eindeutigen Keywords])

ROUTER_RULES = [
    # 1. Sehr spezifische Hardware
    ("CPU-Kühler", ["cpu-kühler", "luftkühler", "wasserkühlung", "cpu cooler", "liquid cooler", "aio", "water cooling"]),
    ("Gehäuselüfter", ["gehäuselüfter", "case fan", "system fan", "lüfter", "fan"]), # 'Lüfter' erst NACH CPU-Kühler prüfen!
    
    # 2. Hauptkomponenten
    ("Mainboard", ["mainboard", "motherboard", "b650", "z790", "x670", "b760", "am5", "lga1700"]), # Chipsätze helfen oft
    ("Grafikkarte", ["grafikkarte", "gpu", "rtx", "radeon", "geforce", "gtx"]),
    ("Prozessor", ["prozessor", "cpu", "intel core", "amd ryzen"]),
    ("Arbeitsspeicher", ["arbeitsspeicher", "ddr4", "ddr5", "dimm", "so-dimm", "ram kit"]),
    
    # 3. Gehäuse & Strom
    ("Gehäuse", ["gehäuse", "midi tower", "big tower", "mini tower", "pc-case"]),
    ("Netzteil", ["netzteil", "power supply", "psu", "atx 3.0", "gold", "platinum"]),
    
    # 4. Speicher & Laufwerke
    ("Speicher", ["ssd", "hdd", "festplatte", "m.2", "nvme", "sata"]),
    ("Laufwerk", ["dvd-brenner", "blu-ray", "laufwerk"]),
    
    # 5. Peripherie & Zubehör (Oft problematisch, daher gut keyworden)
    ("Monitor", ["monitor", "bildschirm", "display", "tft", "oled", "ips"]),
    ("Eingabegeräte", ["maus", "tastatur", "keyboard", "mouse", "keypad"]),
    ("Kabel", ["kabel", "adapter", "hdmi", "displayport", "usb-c", "verlängerung"]),
    ("Mauspad", ["mauspad", "mousepad"]),
    ("Wärmeleitpaste", ["wärmeleitpaste", "thermal compound", "thermal paste"]),
    ("Software", ["windows", "office", "antivirus", "software"]),
]

def classify_product_type(product_name, gtin):
    """
    Der 'Router': Entscheidet, was das Produkt ist.
    Nutzt jetzt die konfigurierbare ROUTER_RULES Liste für die Fast-Lane.
    """
    name_lower = product_name.lower()
    
    # --- 🏎️ FAST LANE (Listen-basiert) ---
    for category, keywords in ROUTER_RULES:
        # Prüfen, ob eines der Keywords im Namen steckt
        for kw in keywords:
            # Wir prüfen mit Wortgrenzen-Logik oder simpler Inklusion
            if kw in name_lower:
                # Debug Ausgabe nur für wichtige Entscheidungen
                # print(f"   🧠 Router (Fast-Lane): '{kw}' erkannt -> {category}")
                return category

    # --- 🧠 AI Router (Fallback für unklare Fälle) ---
    try:
        gtin_info = f"GTIN: {gtin}" if gtin else ""
        
        # Liste der bekannten Kategorien dynamisch aus den Regeln bauen
        known_cats = [rule[0] for rule in ROUTER_RULES]
        cat_list_str = ", ".join(known_cats)
        
        response = client.chat.completions.create(
            model=MODEL_NAME, 
            messages=[
                {"role": "system", "content": f"""
                Du bist ein präziser Hardware-Klassifizierer.
                Ordne den Artikel EINER der folgenden Kategorien zu:
                [{cat_list_str}, Sonstiges]
                
                Antworte NUR mit dem exakten Wort der Kategorie.
                """},
                {"role": "user", "content": f"Produkt: {product_name}\n{gtin_info}"}
            ],
            temperature=0.0
        )
        category = response.choices[0].message.content.strip()
        
        # Manchmal antwortet die KI mit "Kategorie: Prozessor" -> bereinigen
        if ":" in category: category = category.split(":")[-1].strip()
            
        print(f"   🧠 AI-Router: '{product_name[:30]}...' -> {category}")
        return category
        
    except Exception as e:
        print(f"   ⚠️ Router-Fehler: {e}")
        return "Sonstiges"

def get_prompt_by_category(product_name, gtin):
    """ 
    Wählt den Prompt basierend auf der Entscheidung.
    """
    
    category = classify_product_type(product_name, gtin)
    cat_lower = category.lower()

    # Basis-Prompt (unverändert)
    base_prompt = f"""
    Du bist ein technischer Hardware-Experte für Datenpflege.
    Produkt: {product_name}
    GTIN: {gtin}
    
    Suche nach den offiziellen, vollständigen technischen Datenblättern.
    
    REGELN (STRENG BEFOLGEN):
    1. Wenn Info unauffindbar nach Recherche -> "N/A".
    2. Rate nicht.
    3. EINHEITEN PFLICHT: Schreibe "3.5 GHz" statt "3.5".
    4. SONDERZEICHEN: Nutze "¦" als Trenner in Listen, wenn nötig.
    5. FORMATIERUNG: Nutze NIEMALS "Action:". Nutze AUSSCHLIESSLICH das Format:
       Final Answer:
       ```json
       {{ ... }}
       ```
    6. ANTI-LOOP REGEL: Suche maximal 3-4 Mal. Brich NIEMALS ohne JSON ab!
    """

    # === Dispatcher Logik ===
    # Hier prüfen wir nun auf die Kategorien, die der Router zurückgegeben hat.
    
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

    elif "gehäuselüfter" in cat_lower:
        return base_prompt + """
        Kategorie: Gehäuselüfter
        ERSTELLE EIN HIERARCHISCHES JSON (Nested).
        
        SPEZIAL-ANWEISUNG FÜR "NEUTRAL" / GENERISCHE ARTIKEL:
        Wenn der Artikel "Neutral" oder keinen Markennamen hat:
        1. Suche NICHT im Internet nach Datenblättern.
        2. Leite die Größe aus dem Namen ab (z.B. "120x120" -> 120 mm).
        3. Fülle den Rest mit plausiblen Standardwerten (Schwarz, 1200 rpm, 3-Pin/4-Pin).
        
        Benötigte JSON-Struktur:
        {
            "Allgemein": {
                "Gerätetyp": "Gehäuselüfter",
                "Modell": "z.B. Generic 120mm",
                "Farbe": "z.B. Schwarz",
                "Paketmenge": "1"
            },
            "Technische Daten": {
                "Lüfterdurchmesser": "z.B. 120 mm",
                "Lüfterhöhe": "z.B. 25 mm",
                "Rotationsgeschwindigkeit": "z.B. 1200 rpm",
                "Luftstrom": "N/A",
                "Geräuschpegel": "z.B. 25 dBA",
                "Lager": "Gleitlager"
            },
            "Anschlüsse & Features": {
                "Stromanschluss": "3-Pin / 4-Pin PWM",
                "Beleuchtung": "Keine",
                "Besonderheiten": "N/A"
            }
        }
        """
        
    elif "monitor" in cat_lower:
        return base_prompt + """
        Kategorie: Monitor
        ERSTELLE EIN HIERARCHISCHES JSON (Nested).
        
        WICHTIG ZU AUFLÖSUNG: Gib das Format "BxH" an (z.B. 1920x1080).
        WICHTIG ZU ANSCHLÜSSEN: Zähle die Ports genau (z.B. 2 x HDMI, 1 x DisplayPort).
        
        Benötigte JSON-Struktur:
        {
            "Allgemein": {
                "Gerätetyp": "z.B. LED-hintergrundbeleuchteter LCD-Monitor",
                "Modell": "z.B. Odyssey G5",
                "Farbe": "z.B. Schwarz"
            },
            "Display": {
                "Diagonale": "z.B. 27 Zoll (oder 68.6 cm)",
                "Auflösung": "z.B. 2560 x 1440 (WQHD)",
                "Bildwiederholrate": "z.B. 144 Hz",
                "Reaktionszeit": "z.B. 1 ms (MPRT)",
                "Panel-Typ": "z.B. IPS oder VA",
                "Helligkeit": "z.B. 300 cd/m²",
                "Kontrast": "z.B. 1000:1"
            },
            "Schnittstellen": {
                "Anschlüsse": "Liste (z.B. 1 x DisplayPort 1.2, 2 x HDMI 2.0, 1 x Kopfhörer)"
            },
            "Verschiedenes": {
                "Besonderheiten": "z.B. AMD FreeSync Premium, Höhenverstellbar, Pivot",
                "Zubehör": "z.B. HDMI-Kabel, Stromkabel"
            },
            "Energieversorgung": {
                "Stromverbrauch SDR (Eingeschaltet)": "z.B. 25 kWh/1000h",
                "Energieeffizienzklasse": "z.B. Klasse F"
            }
        }
        """

    elif "netzteil" in cat_lower:
        return base_prompt + """
        Kategorie: Netzteil
        ERSTELLE EIN HIERARCHISCHES JSON.
        
        WICHTIG: 
        1. Unterscheide Typ: "Luftkühler" oder "AiO Wasserkühlung".
        2. Sockel: Liste ALLE kompatiblen Sockel auf (z.B. AM4, AM5, LGA1700).
        3. Maße: Bei Luftkühlern ist die HÖHE (mm) extrem wichtig. Bei AiO die RADIATOR-GRÖSSE.
        
        Benötigte JSON-Struktur:
        {
            "Allgemein": {
                "Gerätetyp": "Luftkühler oder AiO Wasserkühlung",
                "Modell": "z.B. Dark Rock Pro 5",
                "TDP-Klasse": "z.B. 250 Watt (oder N/A)"
            },
            "Kompatibilität": {
                "Sockel": "Liste (z.B. AM4, AM5, LGA115x, LGA1200, LGA1700, LGA1851)"
            },
            "Technische Daten": {
                "Bauhöhe (nur Kühler)": "z.B. 165 mm (Wichtig für Gehäuse!)",
                "Radiatorgröße": "z.B. 240 mm, 360 mm (Nur bei AiO, sonst N/A)",
                "Lüftergröße": "z.B. 120 mm",
                "Lautstärke": "z.B. 24.3 dBA"
            },
            "Beleuchtung & Features": {
                "Beleuchtung": "z.B. ARGB, RGB oder Keine",
                "Anschluss": "z.B. 4-Pin PWM, 3-Pin ARGB",
                "Besonderheiten": "z.B. Display, Silent Wings Lüfter"
            }
        }
        """

    elif "prozessor" in cat_lower:
        return base_prompt + """
        Kategorie: Prozessor
         ERSTELLE EIN HIERARCHISCHES JSON (Nested).
        
        ANWEISUNG ZU TAKTRATEN (Intel/Hybrid):
        Wenn es unterschiedliche Kerne gibt (Performance/Efficiency), gib die Taktraten und Anzahl getrennt an.
        Format: "P-Core: 3.5 GHz ¦ E-Core: 2.4 GHz"
        
        Benötigte JSON-Struktur:
        {
            "Allgemein": {
                "Produkttyp": "Prozessor",
                "Codename": "z.B. Raptor Lake Refresh oder Raphael",
                "Serie": "z.B. Core i9 oder Ryzen 9",
                "Modell": "z.B. 14900K oder 7950X"
            },
            "Prozessor": {
                "Sockel": "z.B. LGA1700 oder AM5",
                "Gesamtkerne": "z.B. 24",
                "Gesamtthreads": "z.B. 32",
                "P-Cores (Anzahl)": "z.B. 8 (oder 'N/A' bei AMD)",
                "E-Cores (Anzahl)": "z.B. 16 (oder 'N/A' bei AMD)",
                "Taktfrequenz Basis": "z.B. 3.2 GHz (P-Core)",
                "Taktfrequenz Turbo": "z.B. 6.0 GHz (P-Core)",
                "Taktfrequenz E-Core Basis": "z.B. 2.4 GHz",
                "Taktfrequenz E-Core Turbo": "z.B. 4.4 GHz",
                "L2 Cache": "MB",
                "L3 Cache": "MB",
                "TDP": "z.B. 125 W",
                "TDP (Max/Turbo)": "z.B. 253 W",
                "Chipsatz-Kompatibilität": "z.B. Z790, B760, H770 (Liste)"
            },
            "Speicher-Controller": {
                "Unterstützter Speichertyp": "z.B. DDR5, DDR4",
                "Max. Taktfrequenz DDR5": "z.B. 5600 MHz",
                "Max. Taktfrequenz DDR4": "z.B. 3200 MHz",
                "Max. Speicherkapazität": "z.B. 192 GB"
            },
            "Integrierte Grafik": {
                "Typ": "z.B. Intel UHD Graphics 770 oder Radeon Graphics (oder 'Keine')",
                "Basisfrequenz": "MHz"
            },
            "Verschiedenes": {
                "Verpackung": "z.B. Box oder Tray",
                "Kühler im Lieferumfang": "Ja / Nein"
            }
        }
        """

    elif "grafikkarte" in cat_lower:
        return base_prompt + """
        Kategorie: Grafikkarte
        ERSTELLE EIN HIERARCHISCHES JSON (Nested).
        
        WICHTIG ZU ABMESSUNGEN: Gib alle Maße in 'mm' an.
        WICHTIG ZU STROM: Liste die genauen Stecker auf (z.B. '1 x 16-polig (12VHPWR)' oder '2 x 8-polig').
        
        Benötigte JSON-Struktur:
        {
            "Allgemein": {
                "Gerätetyp": "Grafikkarten",
                "Chipsatz-Hersteller": "NVIDIA / AMD / Intel",
                "Grafikprozessor": "z.B. GeForce RTX 4070 Ti Super",
                "Serie": "z.B. ASUS TUF Gaming",
                "Schnittstelle": "z.B. PCI Express 4.0 x16",
                "Max Auflösung": "z.B. 7680 x 4320",
                "Anzahl der max. unterstützten Bildschirme": "z.B. 4",
                "API-Unterstützung": "z.B. OpenGL 4.6, DirectX 12 Ultimate"
            },
            "Arbeitsspeicher": {
                "Grösse": "z.B. 16 GB",
                "Technologie": "z.B. GDDR6X",
                "Speichergeschwindigkeit": "z.B. 21 Gbps",
                "Busbreite": "z.B. 256-bit"
            },
            "Systemanforderungen": {
                "Erforderliche Leistungsversorgung": "z.B. 750 W (Empfohlenes Netzteil)",
                "Stromverbrauch (TDP)": "z.B. 285 W",
                "Zusätzliche Anforderungen": "z.B. 1 x 16-poliger Stromanschluss"
            },
            "Verschiedenes": {
                "Zubehör im Lieferumfang": "z.B. Grafikkartenhalterung",
                "Software inbegriffen": "z.B. Gigabyte Control Center",
                "Besonderheiten": "z.B. RGB Fusion, Dual Bios"
            },
            "Abmessungen und Gewicht": {
                "Breite": "mm (Slot-Breite)",
                "Tiefe": "mm (Länge der Karte)",
                "Höhe": "mm (Höhe der Karte)",
                "Slot-Belegung": "z.B. 2.5 oder 3"
            }
        }
        """

    elif "mainboard" in cat_lower:
        return base_prompt + """
        Kategorie: Mainboard
        ERSTELLE EIN HIERARCHISCHES JSON (Nested).
        
        WICHTIG ZU ANSCHLÜSSEN (Zwingend beachten!):
        1. Liste JEDEN Anschluss einzeln auf.
        2. Format: "Anzahl x Typ". Beispiel: "1 x HDMI, 1 x DisplayPort, 4 x USB 2.0".
        3. Unterscheide strikt zwischen "Rückseite" (I/O Shield) und "Intern" (Header auf dem PCB).
        4. Zähle die RAM-Slots (meist 2 oder 4).
        
        Benötigte JSON-Struktur:
        {
            "Allgemein": {
                "Produkttyp": "Motherboard - z.B. ATX",
                "Chipsatz": "z.B. AMD B650",
                "Prozessorsockel": "z.B. Socket AM5",
                "Kompatible Prozessoren": "z.B. Ryzen 7000/8000 Serie"
            },
            "Unterstützter RAM": {
                "Max. Größe": "z.B. 192 GB",
                "Technologie": "z.B. DDR5",
                "Bustakt": "z.B. 6400(OC) / 6000(OC) / 5200 MHz",
                "Anzahl Steckplätze": "z.B. 4 (WICHTIG: Zahl eintragen!)",
                "Unterstützte RAM-Integritätsprüfung": "Non-ECC / ECC",
                "Registriert oder gepuffert": "Unbuffered"
            },
            "Audio": {
                "Typ": "HD Audio (8-Kanal)",
                "Audio Codec": "z.B. Realtek ALC897",
                "Kompatibilität": "High Definition Audio"
            },
            "LAN": {
                "Netzwerkcontroller": "z.B. Realtek 2.5GbE LAN chip",
                "Netzwerkschnittstellen": "2.5 Gigabit Ethernet, Bluetooth 5.3, Wi-Fi 6E"
            },
            "Erweiterung / Konnektivität": {
                "Erweiterungssteckplätze": "Liste (z.B. 1 x PCIe 5.0 x16, 2 x PCIe 3.0 x1)",
                "Speicherschnittstellen": "Liste (z.B. 4 x SATA-600, 3 x M.2)",
                "Schnittstellen (Intern)": "Liste aller Header (z.B. 1 x USB-C Header, 2 x USB 3.0 Header, 2 x ARGB Gen2, 1 x RGB 4-Pin, 1 x CPU Fan)",
                "Schnittstellen (Rückseite)": "Liste aller Ports (z.B. 1 x HDMI, 1 x DisplayPort, 1 x USB-C 3.2, 4 x USB 3.0, 1 x RJ-45, 3 x Audio Jacks, 2 x Wi-Fi Antenna)",
                "Stromanschlüsse": "z.B. 1 x 24-poliger Hauptstromanschluss, 2 x 8-poliger ATX12V-Anschluss"
            },
            "Besonderheiten": {
                "BIOS-Typ": "AMI",
                "BIOS-Funktionen": "z.B. WfM 2.0, UEFI BIOS, Q-Flash Plus",
                "Hardwarefeatures": "z.B. Q-Flash Plus, Smart Fan 6, RGB Fusion 2.0, Mystic Light"
            },
            "Abmessungen": {
                "Breite": "cm",
                "Tiefe": "cm"
            }
        }
        """

    elif "arbeitsspeicher" in cat_lower or "ram" in cat_lower:
        return base_prompt + """
        Kategorie: RAM
        ERSTELLE EIN HIERARCHISCHES JSON (Nested) passend zur JTL-Vorlage.
        
        ANWEISUNG ZU "RAM-LEISTUNG":
        Versuche hier, die verschiedenen Profile (SPD, XMP, EXPO) aufzulisten. 
        Format: "Profilname - Takt - Spannung - Timings" (Nutze '¦' als Trenner zwischen den Profilen).
        
        Benötigte JSON-Struktur:
        {
            "Allgemein": {
                "Kapazität": "z.B. 32 GB: 2 x 16 GB",
                "Erweiterungstyp": "Generisch",
                "Breite": "mm",
                "Tiefe": "mm",
                "Höhe": "mm"
            },
            "Arbeitsspeicher": {
                "Typ": "z.B. DRAM Speicher-Kit",
                "Technologie": "z.B. DDR5 SDRAM",
                "Formfaktor": "z.B. DIMM 288-PIN",
                "Geschwindigkeit": "z.B. 6000 MHz (PC5-48000)",
                "Latenzzeiten": "z.B. CL30 (30-36-36)",
                "Datenintegritätsprüfung": "z.B. On-die ECC oder Non-ECC",
                "Besonderheiten": "Features (z.B. Intel XMP 3.0, AMD EXPO, RGB Beleuchtung, Kühlkörper)",
                "Modulkonfiguration": "z.B. 2048 x 64",
                "Spannung": "z.B. 1.35 V",
                "RAM-Leistung": "Liste der Profile (z.B. SPD - 4800 MHz... ¦ XMP - 6000 MHz...)"
            },
            "Verschiedenes": {
                "Farbkategorie": "z.B. Schwarz",
                "Kennzeichnung": "z.B. JEDEC, UL"
            },
            "Herstellergarantie": {
                "Service und Support": "z.B. Begrenzte lebenslange Garantie"
            }
        }
        """

    elif "speicher" in cat_lower or "ssd" in cat_lower or "hdd" in cat_lower:
        return base_prompt + """
        Kategorie: Speicher (SSD/HDD)
        ERSTELLE EIN HIERARCHISCHES JSON (Nested).
        
        WICHTIG ZU TYP:
        Unterscheide genau:
        - "M.2 NVMe" (PCIe Schnittstelle)
        - "M.2 SATA" (SATA Schnittstelle aber M.2 Formfaktor)
        - "SSD" (2.5 Zoll SATA)
        - "HDD" (3.5 Zoll magnetisch)
        
        WICHTIG ZU GESCHWINDIGKEIT:
        Gib Leserate/Schreibrate in MB/s an (z.B. 7000 MB/s).
        
        Benötigte JSON-Struktur:
        {
            "Allgemein": {
                "Gerätetyp": "z.B. Solid State Drive - intern",
                "Kapazität": "z.B. 1 TB (oder 500 GB)",
                "Formfaktor": "z.B. M.2 2280 oder 2.5\" oder 3.5\"",
                "Schnittstelle": "z.B. PCIe 4.0 x4 (NVMe) oder SATA 6Gb/s",
                "Besonderheiten": "Features (z.B. 3D NAND, S.M.A.R.T.)"
            },
            "Leistung": {
                "Übertragungsrate Laufwerk": "z.B. 600 MBps (extern)",
                "Interner Datendurchsatz (Lesen)": "z.B. 7450 MBps",
                "Interner Datendurchsatz (Schreiben)": "z.B. 6900 MBps",
                "Spindelgeschwindigkeit": "z.B. 7200 rpm (Nur bei HDD)",
                "MTBF": "z.B. 1.5 Mio Stunden"
            },
            "Abmessungen und Gewicht": {
                "Breite": "mm",
                "Tiefe": "mm",
                "Höhe": "mm"
            }
        }
        """

    elif "gehäuse" in cat_lower:
        return base_prompt + """
        Kategorie: Gehäuse
        ERSTELLE EIN HIERARCHISCHES JSON (Nested).
        
        WICHTIG ZU MAßEN: Gib alle Längen/Höhen in 'mm' an.
        WICHTIG ZU LÜFTERN: Unterscheide 'Installiert' (ab Werk) und 'Unterstützt' (Maximal).
        
        Benötigte JSON-Struktur:
        {
            "Allgemein": {
                "Formfaktor": "z.B. Midi Tower",
                "Max. Mainboard-Größe": "z.B. ATX (oder E-ATX, Micro-ATX)",
                "Unterstützte Mainboards": "Liste (z.B. ATX, microATX, Mini-ITX)",
                "Anzahl interner Einbauschächte": "z.B. 2 x 3.5\" ¦ 2 x 2.5\"",
                "Fenster": "Ja / Nein (z.B. Seitenfenster aus gehärtetem Glas)",
                "Farbe": "z.B. Schwarz",
                "Besonderheiten": "Features (z.B. Staubfilter, Kabelmanagement, RGB-Steuerung)"
            },
            "Kühlsystem (Installiert)": {
                "Lüfter (Vorne)": "z.B. 3 x 120 mm ARGB",
                "Lüfter (Hinten)": "z.B. 1 x 120 mm",
                "Lüfter (Oben)": "z.B. N/A"
            },
            "Kühlsystem (Unterstützt)": {
                "Lüfterhalterungen (Gesamt)": "z.B. 6 (Summe aller Plätze)",
                "Radiatorgröße (Vorne)": "z.B. 360 mm",
                "Radiatorgröße (Oben)": "z.B. 240 mm",
                "Radiatorgröße (Hinten)": "z.B. 120 mm"
            },
            "Erweiterung / Konnektivität": {
                "Erweiterungssteckplätze": "Anzahl (z.B. 7)",
                "Schnittstellen": "z.B. 2 x USB 3.0 ¦ 1 x USB-C ¦ 1 x Audio/Mic"
            },
            "Systemanforderungen": {
                "Max. Höhe CPU-Kühler": "mm",
                "Max. Länge Grafikkarte": "mm",
                "Max. Länge Netzteil": "mm"
            },
            "Abmessungen und Gewicht": {
                "Breite": "mm",
                "Tiefe": "mm",
                "Höhe": "mm",
                "Gewicht": "kg"
            }
        }
        """
        
        

    else:
        # Fallback für alles, was wir noch nicht definiert haben
        return base_prompt + """
        Identifiziere die Kategorie selbst.
        Erstelle ein sinnvolles, hierarchisches JSON.
        """