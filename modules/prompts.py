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
    
    if "cpu_kuehler" in cat_lower or "cpu-kühler" in cat_lower or "prozessor-kühler" in cat_lower:
        return base_prompt + """
        Kategorie: Prozessor-Kühler (CPU Cooler)
        ERSTELLE EIN HIERARCHISCHES JSON (IT-Scope Datenblatt Style).

        CRITICAL INSTRUCTIONS:
        1. Kompatibilität: Liste ALLE unterstützten Sockel auf (z.B. LGA1700, AM5, AM4, LGA1200). Das ist das wichtigste Feld!
        2. Maße: Die HÖHE ist kritisch für Gehäuse-Kompatibilität. Suche explizit danach.
        3. Lüfter: Details zu RPM, Lautstärke (dBA/Sone) und Anschluss (4-Pin PWM) sind Pflicht.
        4. Material: Unterscheide zwischen Kühlerboden (Kupfer) und Lamellen (Alu).

        Benötigte JSON-Struktur:
        {
            "Allgemein": {
                "Produkttyp": "z.B. Prozessor-Luftkühler",
                "Packungsinhalt": "z.B. Wärmeleitpaste, Montagekit",
                "Breite": "cm",
                "Tiefe": "cm",
                "Höhe": "cm (Wichtig!)",
                "Gewicht": "g oder kg",
                "Farbe": "z.B. Schwarz / Weiß"
            },
            "Kühlkörper und Lüfter": {
                "Kompatibel mit": "Liste der Sockel (z.B. LGA1700 Socket, Socket AM5, LGA1200)",
                "Kühlermaterial": "z.B. Aluminium und Kupfer",
                "Lüfterdurchmesser": "z.B. 120 mm",
                "Gebläsehöhe": "Dicke des Lüfters (z.B. 25 mm)",
                "Lüfterlager": "z.B. Hydro Bearing oder Fluid Dynamic Bearing",
                "Drehgeschwindigkeit": "z.B. 500-1800 U/min",
                "Luftstrom": "z.B. 78 CFM",
                "Luftdruck": "z.B. 2.7 mm",
                "Geräuschpegel": "z.B. 18 - 30 dBA",
                "Netzanschluss": "z.B. PWM, 4-polig",
                "Nennspannung": "12 V",
                "Energieverbrauch": "Watt",
                "Merkmale": "z.B. 4 Heatpipes, Direct Contact Technology, RGB"
            },
            "Verschiedenes": {
                "MTBF": "Lebensdauer (z.B. 60.000 Stunden)",
                "Montagekit": "Mitgeliefert",
                "Kennzeichnung": "z.B. CE, RoHS"
            },
            "Herstellergarantie": {
                "Service und Support": "Dauer (z.B. 2 Jahre)"
            }
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


    elif "netzteil" in cat_lower or "psu" in cat_lower or "power supply" in cat_lower:
        return base_prompt + """
        Kategorie: Netzteil (PSU)
        ERSTELLE EIN HIERARCHISCHES JSON (IT-Scope Datenblatt Style).

        CRITICAL INSTRUCTIONS:
        1. Anschlüsse: Liste GENAU auf, wie viele Stecker vorhanden sind (z.B. "3 x 8-poliger PCI Express", "1 x 16-pin 12VHPWR").
        2. Zertifizierung: Suche nach "80 PLUS" (Gold, Platinum, Titanium, Bronze).
        3. Modularität: Ist es "Voll-modular", "Teil-modular" oder "Nicht modular"?
        4. Ausgangsstrom: Versuche die Ampere-Werte für +3.3V, +5V und +12V zu finden.

        Benötigte JSON-Struktur:
        {
            "Allgemein": {
                "Gerätetyp": "Netzteil - intern",
                "Spezifikationseinhaltung": "z.B. ATX12V 3.0 / EPS12V 2.92",
                "Netzteil-Formfaktor": "z.B. ATX",
                "Farbe": "z.B. Schwarz"
            },
            "Stromversorgungsgerät": {
                "Eingangsspannung": "z.B. Wechselstrom 100-240 V",
                "Leistungskapazität": "Wattzahl (z.B. 850 Watt)",
                "80-PLUS-Zertifizierung": "z.B. 80 PLUS Gold",
                "Modulare Kabelverwaltung": "Ja / Nein",
                "Angaben zu Ausgangsleistungsanschlüssen": "Detaillierte Liste der Kabel (z.B. 1x 24-Pin, 2x EPS, 4x PCIe, 1x 12VHPWR)",
                "Ausgangsstrom": "Ampere-Liste (z.B. +3.3V - 20 A / +5V - 20 A / +12V - 70 A)",
                "Effizienz": "z.B. 90% bei 50% Last (falls verfügbar)"
            },
            "Verschiedenes": {
                "Besonderheiten": "z.B. Lüfter mit Doppelkugellager, Überspannungsschutz (OVP), Zero RPM Mode",
                "Zubehör im Lieferumfang": "z.B. Kabelbinder, Schrauben, Netzkabel",
                "Kühlsystem": "z.B. 135-mm-Lüfter"
            },
            "Abmessungen und Gewicht": {
                "Breite": "cm",
                "Tiefe": "cm",
                "Höhe": "cm",
                "Gewicht": "kg"
            },
            "Herstellergarantie": {
                "Service und Support": "Dauer (z.B. Begrenzte Garantie - 10 Jahre)"
            }
        }
        """

    elif "prozessor" in cat_lower or "cpu" in cat_lower:
        return base_prompt + """
        Kategorie: Prozessor (CPU)
        ERSTELLE EIN HIERARCHISCHES JSON (IT-Scope Datenblatt Style).

        CRITICAL INSTRUCTIONS:
        1. Kerne/Takt (Intel Hybrid): Unterscheide ZWINGEND zwischen P-Cores (Performance) und E-Cores (Efficiency) bei Takt und Anzahl.
           Format: "2 GHz (P-Kern) / 1.5 GHz (E-Kern)".
        2. Verpackung: "Box" (Retail, oft mit Kühler) vs. "OEM/Tray" (Nur CPU).
        3. Cache: Nenne L2 und L3 Cache separat oder als "Cache-Speicher-Details".
        4. Grafik: Prüfe auf integrierte Grafik (iGPU). (Achtung: Intel 'F'-Modelle haben KEINE Grafik!).

        Benötigte JSON-Struktur:
        {
            "Allgemein": {
                "Produkttyp": "Prozessor",
                "Prozessorhersteller": "Intel oder AMD",
                "Prozessorfamilie": "z.B. Intel Core i9 oder AMD Ryzen 5",
                "Prozessor": "Modell (z.B. 14900F oder 7600X)",
                "Prozessorsockel": "z.B. FCLGA1700 Socket oder Socket AM5",
                "Box": "Ja / Nein (oder Verpackung: Tray)"
            },
            "Prozessor": {
                "Anz. der Kerne": "Gesamt + Split (z.B. 24 Kerne (8P + 16E))",
                "Anz. der Threads": "Anzahl",
                "Taktfrequenz": "Basis (z.B. 2 GHz (P-Kern) / 1.5 GHz (E-Kern))",
                "Max. Turbo-Taktfrequenz": "Turbo (z.B. 5.8 GHz (P-Kern))",
                "Cache-Speicher": "Gesamt (z.B. 36 MB)",
                "Cache-Speicher-Details": "Details (z.B. Smart Cache - 36 MB ¦ L2 - 32 MB)",
                "Thermal Design Power (TDP)": "Basis-Watt (z.B. 65 W)",
                "Maximale Turbo-Leistung": "Max-Watt (z.B. 219 W)",
                "Herstellungsprozess": "z.B. 10 nm oder 5 nm"
            },
            "Grafik": {
                "Eingebaute Grafikadapter": "Ja / Nein",
                "On-Board Grafikadaptermodell": "Modell (z.B. Intel UHD 770 oder AMD Radeon Graphics)",
                "On-Board Grafikadapter Basisfrequenz": "MHz",
                "Maximale dynamische Frequenz der On-Board Grafikadapter": "MHz"
            },
            "Speicher": {
                "Maximaler interner Speicher, vom Prozessor unterstützt": "z.B. 128 GB",
                "Speichertaktraten, vom Prozessor unterstützt": "z.B. 5200 MHz",
                "Speicherkanäle": "z.B. Dual-channel",
                "ECC": "Ja / Nein"
            },
            "E-/A-Konfiguration": {
                "PCI Express Revision": "z.B. 4.0/5.0",
                "Anz. PCI Express Lanes": "Anzahl"
            },
            "Architektur-Merkmale": {
                "Besonderheiten": "Liste (z.B. Hyper-Threading, DL Boost, AVX2, EXPO, Intel Thread Director)"
            },
            "Verschiedenes": {
                "Verpackung": "z.B. OEM/Tray oder Box",
                "Zubehör im Lieferumfang": "z.B. Kühler (nur wenn Box)"
            }
        }
        """

    elif "grafikkarte" in cat_lower or "gpu" in cat_lower or "graphics card" in cat_lower:
        return base_prompt + """
        Kategorie: Grafikkarte (GPU)
        ERSTELLE EIN HIERARCHISCHES JSON (IT-Scope Datenblatt Style).

        CRITICAL INSTRUCTIONS:
        1. Maße: "Tiefe" ist meist die Länge der Karte (z.B. 33 cm). "Breite" ist die Dicke (Slots, z.B. 5 cm).
        2. Leistung: Unterscheide zwischen "Erforderliche Leistungsversorgung" (Netzteil-Empfehlung, z.B. 750W) und "Leistungsaufnahme" (TBP/TGP der Karte selbst, z.B. 300W).
        3. Kerne: Bei Nvidia "CUDA-Kerne", bei AMD "Stream Prozessoren" (oder Schader-Einheiten) zählen.

        Benötigte JSON-Struktur:
        {
            "Allgemein": {
                "Gerätetyp": "Grafikkarten",
                "Bustyp": "z.B. PCI Express 4.0 x16 oder 5.0",
                "Grafikprozessor": "Voller Name (z.B. NVIDIA GeForce RTX 4070 Ti)",
                "Boost-Takt": "MHz",
                "CUDA-Kerne": "Anzahl (nur bei Nvidia füllen, sonst weglassen oder als 'Stream Prozessoren' labeln)",
                "Max Auflösung": "z.B. 7680 x 4320",
                "Anzahl der max. unterstützten Bildschirme": "Anzahl (z.B. 4)",
                "Schnittstellendetails": "Liste (z.B. 3 x DisplayPort, 1 x HDMI)",
                "API-Unterstützung": "z.B. DirectX 12 Ultimate, OpenGL 4.6",
                "Besonderheiten": "Liste von Features (z.B. Dual BIOS, RGB, Backplate, Raytracing Cores)"
            },
            "Arbeitsspeicher": {
                "Grösse": "z.B. 16 GB",
                "Technologie": "z.B. GDDR6X SDRAM",
                "Speichergeschwindigkeit": "z.B. 21 Gbps",
                "Busbreite": "z.B. 192-bit oder 256-bit"
            },
            "Systemanforderungen": {
                "Erfoderliche Leistungsversorgung": "Empfohlenes Netzteil in Watt (z.B. 750 W)",
                "Zusätzliche Anforderungen": "Stromstecker (z.B. 1x 16-Pin 12VHPWR oder 2x 8-Pin)"
            },
            "Verschiedenes": {
                "Leistungsaufnahme im Betrieb": "Verbrauch der Karte in Watt (z.B. 285 Watt)",
                "Zubehör im Lieferumfang": "z.B. Grafikkartenhalterung, Adapter",
                "Breite": "Dicke der Karte in cm (z.B. 5 cm)",
                "Tiefe": "Länge der Karte in cm (z.B. 30 cm)",
                "Höhe": "Höhe der Karte in cm (z.B. 12 cm)",
                "Gewicht": "kg"
            },
            "Herstellergarantie": {
                "Service und Support": "Dauer (z.B. 3 Jahre)"
            }
        }
        """

    elif "mainboard" in cat_lower or "motherboard" in cat_lower:
        return base_prompt + """
        Kategorie: Mainboard (Motherboard)
        ERSTELLE EIN HIERARCHISCHES JSON (IT-Scope Datenblatt Style).

        CRITICAL INSTRUCTIONS:
        1. RAM: Unterscheide strikt zwischen DDR4 und DDR5. Nenne Max. Größe und Taktraten.
        2. LAN/WLAN: Suche nach "2.5 Gigabit" oder "10 Gigabit". Wenn Wi-Fi dabei ist, nenne den Standard (z.B. Wi-Fi 6E).
        3. Schnittstellen: Trenne strikt zwischen "Schnittstellen" (hinten am Panel) und "Interne Schnittstellen" (Header auf dem Board).
        4. M.2: Zähle die Slots genau (z.B. 2x M.2 oder 3x M.2).

        Benötigte JSON-Struktur (orientiert an IT-Scope):
        {
            "Allgemein": {
                "Produkttyp": "z.B. Motherboard - ATX",
                "Chipsatz": "z.B. Intel Z790 oder AMD B650",
                "Prozessorsockel": "z.B. LGA1700-Sockel oder Socket AM5",
                "Kompatible Prozessoren": "z.B. Unterstützt 12./13./14. Gen Intel Core",
                "Max. Anz. Prozessoren": "1"
            },
            "Unterstützter RAM": {
                "Max. Größe": "z.B. 128 GB",
                "Technologie": "z.B. DDR5",
                "Bustakt": "Liste der Taktraten (z.B. 6000 MHz (O.C.), 5600 MHz, 4800 MHz)",
                "Besonderheiten": "z.B. Dual Channel, XMP, EXPO",
                "Registriert oder gepuffert": "Ungepuffert"
            },
            "Audio": {
                "Typ": "z.B. HD Audio (8-Kanal)",
                "Audio Codec": "z.B. Realtek ALC1220"
            },
            "LAN": {
                "Netzwerkschnittstellen": "z.B. 2.5 Gigabit Ethernet, Wi-Fi 6E, Bluetooth 5.3"
            },
            "Erweiterung/Konnektivität": {
                "Erweiterungssteckplätze": "Liste (z.B. 1x PCIe 5.0 x16, 2x PCIe 3.0 x1)",
                "Speicherschnittstellen": "Liste (z.B. 4x SATA-600, 3x M.2)",
                "Schnittstellen": "Hinten (z.B. 1x HDMI, 1x USB-C 3.2 Gen 2x2, 4x USB 3.2 Gen 1, Audio)",
                "Interne Schnittstellen": "Innen (z.B. 1x USB-C Header, 2x USB 2.0 Header, 1x Thunderbolt Header)",
                "Stromanschlüsse": "z.B. 1x 24-Pin ATX, 2x 8-Pin 12V"
            },
            "Besonderheiten": {
                "BIOS-Typ": "z.B. AMI UEFI",
                "Hardwarefeatures": "Liste der Marketing-Features (z.B. Q-Latch, Digi+ VRM, Aura Sync, M.2 Thermal Guard)"
            },
            "Verschiedenes": {
                "Zubehör im Lieferumfang": "z.B. WLAN-Antenne, SATA-Kabel, Schrauben",
                "Breite": "cm",
                "Tiefe": "cm"
            }
        }
        """

    elif "arbeitsspeicher" in cat_lower or "ram" in cat_lower:
        return base_prompt + """
        Kategorie: Arbeitsspeicher (RAM)
        ERSTELLE EIN HIERARCHISCHES JSON (IT-Scope Datenblatt Style).
        
        Suche nach ALLEN technischen Details. Besonders wichtig sind Spannung, Formfaktor und SPD/XMP Details.

        Benötigte JSON-Struktur:
        {
            "Allgemein": {
                "Kapazität": "z.B. 32 GB (2 x 16 GB)",
                "Erweiterungstyp": "z.B. Generisch",
                "Breite": "mm (falls verfügbar)",
                "Tiefe": "mm (falls verfügbar)",
                "Höhe": "mm (falls verfügbar)"
            },
            "Arbeitsspeicher": {
                "Typ": "z.B. DRAM Speicher-Kit",
                "Technologie": "z.B. DDR5 SDRAM",
                "Formfaktor": "z.B. DIMM 288-PIN oder SO-DIMM 262-PIN",
                "Geschwindigkeit": "z.B. 6000 MHz (PC5-48000)",
                "Latenzzeiten": "z.B. CL36 (36-38-38-76)",
                "Besonderheiten": "z.B. Intel Extreme Memory Profiles (XMP 3.0), AMD EXPO, Heatspreader",
                "Spannung": "z.B. 1.35 V",
                "RAM-Leistung": "z.B. SPD - 4800 MHz - 1.1 V / Tested - 6000 MHz - 1.35 V (Details zu Profilen)"
            },
            "Verschiedenes": {
                "Farbkategorie": "z.B. Schwarz, Weiß, RGB"
            },
            "Herstellergarantie": {
                "Service und Support": "z.B. Begrenzte lebenslange Garantie"
            }
        }
        """

    elif "speicher" in cat_lower or "ssd" in cat_lower or "hdd" in cat_lower or "festplatte" in cat_lower:
        return base_prompt + """
        Kategorie: Speicher (SSD / HDD)
        ERSTELLE EIN HIERARCHISCHES JSON (IT-Scope Datenblatt Style).

        CRITICAL INSTRUCTIONS:
        1. Geschwindigkeit: Lesen/Schreiben in MB/s (z.B. 3500 MB/s).
        2. Kapazität: Exakte Größe (z.B. 1000 GB, 2 TB).
        3. Schnittstelle: PCIe 4.0, SATA III etc.
        4. Formfaktor: M.2 2280, 2.5 Zoll etc.
        5. Haltbarkeit: Suche nach TBW (Total Bytes Written) und MTBF.

        Benötigte JSON-Struktur:
        {
            "Merkmale": {
                "Gerätetyp": "z.B. SSD oder HDD",
                "SSD Speicherkapazität": "z.B. 1000 GB",
                "SSD-Formfaktor": "z.B. M.2 2280",
                "Schnittstelle": "z.B. PCI Express 4.0 x4 (NVMe)",
                "NVMe": "Ja / Nein",
                "Komponente für": "z.B. PC/notebook"
            },
            "Leistung": {
                "Lesegeschwindigkeit": "z.B. 7000 MB/s",
                "Schreibgeschwindigkeit": "z.B. 5000 MB/s",
                "Mittlere Betriebsdauer zwischen Ausfällen (MTBF)": "z.B. 1.500.000 h",
                "TBW": "z.B. 600 TB"
            },
            "Betriebsbedingungen": {
                "Betriebstemperatur": "z.B. 0 - 70 °C",
                "Temperaturbereich bei Lagerung": "z.B. -40 - 85 °C"
            },
            "Gewicht und Abmessungen": {
                "Breite": "mm",
                "Tiefe": "mm",
                "Höhe": "mm",
                "Gewicht": "g"
            },
            "Technische Details": {
                "Nachhaltigkeitszertifikate": "z.B. RoHS, CE"
            }
        }
        """
        
    elif "monitor" in cat_lower or "tft" in cat_lower or "display" in cat_lower or "bildschirm" in cat_lower:
        return base_prompt + """
        Kategorie: Monitor (TFT / Display)
        ERSTELLE EIN HIERARCHISCHES JSON (IT-Scope Datenblatt Style).

        CRITICAL INSTRUCTIONS:
        1. Auflösung/Hz: Suche nach Details pro Anschluss (z.B. "DP: 165Hz, HDMI: 144Hz").
        2. Panel: Welcher Typ? (IPS, VA, TN, OLED, QD-OLED).
        3. Ergonomie: Höhenverstellbar? Neigbar? VESA-Mount vorhanden?
        4. Farbe: Farbraumabdeckung (sRGB, DCI-P3, Adobe RGB) detailliert listen.

        Benötigte JSON-Struktur:
        {
            "Allgemein": {
                "Gerätetyp": "z.B. LED-hintergrundbeleuchteter LCD-Monitor",
                "Energie Effizienzklasse": "z.B. Klasse F",
                "Diagonalabmessung": "z.B. 27 Zoll (69 cm)",
                "Geschwungener Bildschirm": "Ja (1500R) / Nein",
                "Panel-Typ": "z.B. IPS, VA, Rapid VA",
                "Seitenverhältnis": "z.B. 16:9",
                "Native Auflösung": "z.B. WQHD 2560 x 1440 (DisplayPort: 170 Hz)",
                "Helligkeit": "z.B. 400 cd/m²",
                "Kontrast": "z.B. 1000:1 / 100M:1 (dynamisch)",
                "HDR-Zertifizierung": "z.B. DisplayHDR 400",
                "Reaktionszeit": "z.B. 1 ms (GtG), 0.5 ms (MPRT)",
                "Farbunterstützung": "z.B. 1.07 Mrd. Farben (10-bit)"
            },
            "Bildqualität": {
                "Farbraum": "Detaillierte Liste (z.B. 120% sRGB, 95% DCI-P3)",
                "Besonderheiten": "z.B. Flicker-Free, Low Blue Light, AMD FreeSync Premium"
            },
            "Konnektivität": {
                "Schnittstellen": "Liste (z.B. 2x HDMI 2.1, 1x DisplayPort 1.4, 1x USB-C mit 65W PD, Audio Out)"
            },
            "Mechanisch": {
                "Einstellungen der Anzeigeposition": "z.B. Höhe, Neigung, Drehung (Pivot)",
                "Höheneinstellung": "z.B. 130 mm",
                "VESA-Halterung": "z.B. 100 x 100 mm",
                "Neigungswinkel": "z.B. -5/+20"
            },
            "Stromversorgung": {
                "Eingangsspannung": "z.B. Wechselstrom 100-240 V",
                "Stromverbrauch SDR (eingeschaltet)": "kWh/1000h",
                "Stromverbrauch HDR (eingeschaltet)": "kWh/1000h"
            },
            "Abmessungen und Gewicht": {
                "Details": "Maße mit/ohne Fuß (z.B. Mit Fuß: 61 x 45 x 20 cm - 5.8 kg)"
            },
            "Herstellergarantie": {
                "Service und Support": "Dauer (z.B. 3 Jahre)"
            }
        }
        """    

    elif "gehäuse" in cat_lower:
        return base_prompt + """
        Kategorie: Gehäuse (PC Case)
        ERSTELLE EIN HIERARCHISCHES JSON (IT-Scope Datenblatt Style).

        CRITICAL INSTRUCTIONS (ANTI-HALLUCINATION):
        1. Formfaktor-Check: Ein "Micro-ATX" Gehäuse unterstützt KEIN Standard-ATX Mainboard! Prüfe das genau.
        2. Lüfter: Wenn das Netzteil (PSU) vorne montiert wird (z.B. bei Mesh-Gehäusen wie AP201), gibt es vorne KEINE Lüfter!
        3. CPU-Kühler: Suche nach dem exakten mm-Wert. Rate nicht "180mm", wenn es oft 170mm oder 160mm sind.
        4. Wenn eine Info fehlt, schreibe "N/A" statt zu raten.

        Benötigte JSON-Struktur:
        {
            "Allgemein": {
                "Formfaktor": "z.B. Midi Tower, Mini Tower, MicroATX Case",
                "Max. Mainboard-Größe": "Der größte unterstützte Standard (z.B. Micro-ATX)",
                "Unterstützte Motherboards": "Liste der Formate (WICHTIG: Kein ATX bei mATX-Gehäusen!)",
                "Seitenplatte mit Fenster": "Ja / Nein",
                "Seitliches Plattenmaterial mit Fenster": "z.B. Gehärtetes Glas (Tempered Glass)",
                "Produktmaterial": "z.B. Stahl, Mesh",
                "Farbe": "z.B. Schwarz, Weiß",
                "Anzahl interner Einbauschächte": "Gesamtanzahl 2.5/3.5 Zoll",
                "Kühlsystem": "Exakte Positionen (Vorne/Oben/Hinten/Unten). Beachte PSU-Position!",
                "Max. Höhe des CPU-Kühlers": "mm (Exakter Wert!)",
                "Maximale Länge Videokarte": "mm",
                "Maximallänge der Stromversorgung": "mm",
                "Systemgehäuse-Merkmale": "z.B. Mesh-Design, Werkzeuglose Montage"
            },
            "Erweiterung / Konnektivität": {
                "Erweiterungseinschübe": "Detail-Liste",
                "Erweiterungssteckplätze": "Anzahl (z.B. 4 bei mATX, 7 bei ATX)",
                "Schnittstellen": "Front-Panel Anschlüsse (USB-C, Audio etc.)"
            },
            "Stromversorgung": {
                "Stromversorgungsgerät": "z.B. Keine Spannungsversorgung",
                "Spezifikationseinhaltung": "z.B. ATX"
            },
            "Abmessungen und Gewicht": {
                "Breite": "mm",
                "Tiefe": "mm",
                "Höhe": "mm",
                "Gewicht": "kg"
            },
            "Herstellergarantie": {
                "Service und Support": "Dauer"
            }
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
        ERSTELLE EIN HIERARCHISCHES JSON (IT-Scope Datenblatt Style).

        CRITICAL INSTRUCTIONS:
        1. Anschlüsse: Unterscheide ZWINGEND zwischen Stecker (Male) und Buchse (Female). Beispiel: "USB-C Stecker auf HDMI Buchse".
        2. Typ: Ist es ein Adapter (kurz/fest) oder ein Kabel (Länge)?
        3. Specs: Nenne Standards wie HDMI 2.1, Cat7, USB 3.2 Gen 2.
        4. Video: Bei Videokabeln Max. Auflösung (z.B. 4K@60Hz) suchen.

        Benötigte JSON-Struktur:
        {
            "Allgemein": {
                "Kabeltyp": "z.B. Netzwerkkabel - CAT 6a oder Videokabel - Adapter",
                "Länge": "z.B. 2 m (oder N/A bei kompakten Adaptern)",
                "Farbe": "z.B. Schwarz",
                "Außenmaterial": "z.B. PVC, Gewebeummantelung (Nylon)",
                "Schirmungsmaterial": "z.B. Aluminiumfolie (bei hochwertigen Kabeln)"
            },
            "Konnektivität": {
                "Anschluss (1. Ende)": "z.B. 19-poliger HDMI Typ A - Stecker",
                "Anschluss (2. Ende)": "z.B. 19-poliger HDMI Typ A - Stecker",
                "Steckerbeschichtung": "z.B. Gold"
            },
            "Technische Daten": {
                "Besonderheiten": "z.B. 4K Unterstützung, Ethernet-Kanal (HEC), HDR-Support, Rastnasenschutz",
                "Max. Übertragungsrate": "z.B. 48 Gbps (HDMI 2.1) oder 10 Gbit/s (Netzwerk)",
                "Standard": "z.B. HDMI 2.1 oder USB 3.2 Gen 2x2"
            },
            "Herstellergarantie": {
                "Service und Support": "Dauer (z.B. 2 Jahre)"
            }
        }
        """
        
    elif "soundkarte" in cat_lower or "sound card" in cat_lower or "audio interface" in cat_lower:
        return base_prompt + """
        Kategorie: Soundkarte (Audio Interface)
        ERSTELLE EIN HIERARCHISCHES JSON (IT-Scope Datenblatt Style).

        CRITICAL INSTRUCTIONS:
        1. Kanäle: 5.1, 7.1 oder Stereo?
        2. Qualität: Suche nach Bit-Tiefe (z.B. 24-bit) und Abtastrate (z.B. 192kHz).
        3. SNR: Signal-Rausch-Verhältnis in dB (z.B. 106 dB oder 122 dB).
        4. Anschlüsse: Optisch (Toslink)? Kopfhörerverstärker?

        Benötigte JSON-Struktur:
        {
            "Audio": {
                "Gerätetyp": "z.B. Soundkarte (Intern) oder USB-Audio-Interface",
                "Audio Kanäle": "z.B. 7.1 Kanäle",
                "Audioqualität": "z.B. 24 Bit",
                "Digital-Analog-Umwandlung": "z.B. 24-bit/192kHz",
                "Line-Out Signal-Rausch-Verhältnis (SNR)": "z.B. 106 dB",
                "Chipsatz": "z.B. Creative Sound Core3D"
            },
            "Anschlüsse und Schnittstellen": {
                "Hostschnittstelle": "z.B. PCI-E oder USB 2.0",
                "Optischer Audio-Digitalausgang": "Ja / Nein (oder Anzahl)",
                "Kopfhörerausgänge": "Anzahl (z.B. 1)",
                "Mikrofon-Eingang": "Ja / Nein",
                "Line-in": "Ja / Nein",
                "Line-out": "Ja / Nein"
            },
            "Systemanforderung": {
                "Unterstützt Windows-Betriebssysteme": "Ja / Nein"
            },
            "Herstellergarantie": {
                "Service und Support": "Dauer (z.B. 2 Jahre)"
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
        ERSTELLE EIN HIERARCHISCHES JSON (IT-Scope Datenblatt Style).

        CRITICAL INSTRUCTIONS:
        1. Auflösung: Unterscheide zwischen Foto-Megapixeln und Video-Auflösung (z.B. 1920 x 1080).
        2. Framerate: Wichtig für Streamer (30 fps vs 60 fps).
        3. Features: Autofokus? Privacy Cover? Ringlicht?
        4. Mikrofon: Stereo oder Mono?

        Benötigte JSON-Struktur:
        {
            "Allgemein": {
                "Gerätetyp": "Webcam",
                "Modell": "Name",
                "Farbe": "z.B. Schwarz",
                "Anschlusstechnik": "z.B. Kabelgebunden (USB 2.0 / 3.0)"
            },
            "Video": {
                "Max. Digitalvideo-Auflösung": "z.B. 1920 x 1080 (Full HD) oder 3840 x 2160 (4K)",
                "Max. Bildrate": "z.B. 60 fps (bei 1080p)",
                "Digitales Zoom": "z.B. 4x (falls verfügbar)",
                "Fokus-Einstellung": "z.B. Autofokus / Fixfokus"
            },
            "Audio": {
                "Audio-Unterstützung": "Ja: Integriertes Mikrofon",
                "Mikrofon-Typ": "z.B. Stereo / Dual-Mikrofon"
            },
            "Verschiedenes": {
                "Leistungsmerkmale": "z.B. Privacy Shutter, Rauschunterdrückung, Stativgewinde, RightLight Technologie",
                "Zubehör im Lieferumfang": "z.B. Stativ, USB-Kabel"
            },
            "Herstellergarantie": {
                "Service und Support": "Dauer"
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
        
    elif "netzwerkkarte" in cat_lower or "nic" in cat_lower or "network card" in cat_lower or "ethernet adapter" in cat_lower:
        return base_prompt + """
        Kategorie: Netzwerkkarte (NIC)
        ERSTELLE EIN HIERARCHISCHES JSON (IT-Scope Datenblatt Style).

        CRITICAL INSTRUCTIONS:
        1. Schnittstelle: Host (PCI, PCI Express, USB) vs. Netzwerk (RJ-45, SFP).
        2. Geschwindigkeit: 10/100/1000 Mbit/s oder höher (2.5 / 10 Gbit/s)?
        3. Standards: IEEE Liste (z.B. 802.3, 802.3u, 802.1Q).
        4. Features: Wake-on-LAN (WoL), Jumbo Frames, Vollduplex?

        Benötigte JSON-Struktur:
        {
            "Allgemein": {
                "Gerätetyp": "Netzwerkkarte",
                "Formfaktor": "z.B. Plug-in-Karte",
                "Farbe": "z.B. Grün / Schwarz"
            },
            "Anschlüsse und Schnittstellen": {
                "Hostschnittstelle": "z.B. PCI Express x1 oder PCI",
                "Schnittstelle": "z.B. Ethernet",
                "Anzahl Ethernet-LAN-Anschlüsse (RJ-45)": "Anzahl (z.B. 1)",
                "Übertragungstechnik": "Verkabelt"
            },
            "Netzwerk": {
                "Maximale Datenübertragungsrate": "z.B. 1000 Mbit/s",
                "Ethernet LAN Datentransferraten": "z.B. 10,100,1000 Mbit/s",
                "Verkabelungstechnologie": "z.B. 10/100/1000BaseT(X)",
                "Netzstandard": "Liste (z.B. IEEE 802.3, IEEE 802.3u, IEEE 802.1Q)",
                "Vollduplex": "Ja / Nein",
                "Jumbo Frames Unterstützung": "Ja / Nein",
                "Wake-on-LAN bereit": "Ja / Nein",
                "Unterstützung Datenflusssteuerung": "Ja / Nein"
            },
            "Systemanforderung": {
                "Unterstützt Windows-Betriebssysteme": "Liste der Versionen",
                "Unterstützte Linux-Betriebssysteme": "Ja / Nein"
            },
            "Betriebsbedingungen": {
                "Temperaturbereich in Betrieb": "z.B. 0 - 40 °C",
                "Temperaturbereich bei Lagerung": "z.B. -40 - 70 °C",
                "Luftfeuchtigkeit in Betrieb": "z.B. 10 - 90 %"
            },
            "Design": {
                "Zertifizierung": "z.B. FCC, CE",
                "Eingebaut": "Ja",
                "LED-Anzeigen": "Ja / Nein"
            },
            "Herstellergarantie": {
                "Service und Support": "Dauer"
            }
        }
        """
        
    elif "netzwerkadapter" in cat_lower or "wlan" in cat_lower or "wifi" in cat_lower or ("adapter" in cat_lower and "netzwerk" in cat_lower):
        return base_prompt + """
        Kategorie: Netzwerkadapter (WLAN / Bluetooth)
        ERSTELLE EIN HIERARCHISCHES JSON (IT-Scope Datenblatt Style).

        CRITICAL INSTRUCTIONS:
        1. Typ: USB-Stick (Extern) oder PCIe-Karte (Intern)?
        2. WLAN-Standard: Wi-Fi 6 (AX), Wi-Fi 5 (AC) oder Wi-Fi 4 (N)?
        3. Geschwindigkeit: Max. Datenrate (z.B. 1200 Mbit/s oder 3000 Mbit/s).
        4. Bluetooth: Version (z.B. 5.0 / 5.2) falls vorhanden.

        Benötigte JSON-Struktur:
        {
            "Allgemein": {
                "Gerätetyp": "Netzwerkadapter",
                "Formfaktor": "z.B. Extern (USB-Stick) oder Intern (PCIe-Karte)",
                "Schnittstellentyp (Bustyp)": "z.B. SuperSpeed USB 3.0 oder PCI Express"
            },
            "Netzwerk": {
                "Anschlusstechnik": "Kabellos",
                "WLAN-Standard": "z.B. Wi-Fi 6 (802.11ax)",
                "Datenübertragungsrate": "z.B. 3000 Mbit/s",
                "Frequenzband": "z.B. 2.4 GHz, 5 GHz",
                "WLAN-Standards": "Liste (z.B. 802.11a/b/g/n/ac/ax)",
                "Bluetooth-Version": "z.B. 5.0 (falls vorhanden, sonst leer)"
            },
            "Antenne": {
                "Antenne": "Intern / Extern",
                "Anzahl der Antennen": "z.B. 2"
            },
            "Verschiedenes": {
                "Verschlüsselungsalgorithmus": "z.B. WPA3, WPA2",
                "Produktzertifizierungen": "z.B. CE, FCC"
            },
            "Systemanforderung": {
                "Erforderliches Betriebssystem": "Liste"
            },
            "Maße und Gewicht": {
                "Breite": "cm",
                "Tiefe": "cm",
                "Höhe": "cm",
                "Gewicht": "g"
            }
        }
        """    
        
    elif "software" in cat_lower or "windows" in cat_lower or "office" in cat_lower or "antivirus" in cat_lower or "esd" in cat_lower or "microsoft" in cat_lower or "adobe" in cat_lower:
        return base_prompt + """
        Kategorie: Software (Betriebssysteme, Office, Antivirus)
        ERSTELLE EIN HIERARCHISCHES JSON.

        CRITICAL INSTRUCTIONS:
        1. Typ: Betriebssystem, Office-Anwendung oder Sicherheit/Antivirus?
        2. Edition: Home, Pro, Enterprise, Personal, Family?
        3. Sprache: Deutsch, Englisch, Multilingual?
        4. Lizenz: OEM (Systembuilder), Retail (Box), ESD (Download), DSP/SB.
        5. Geräteanzahl: 1 PC, 5 Geräte, 1 Benutzer?

        Benötigte JSON-Struktur:
        {
            "Allgemein": {
                "Gerätetyp": "Software",
                "Titel": "Name der Software (z.B. Microsoft Windows 11 Pro)",
                "Hersteller": "z.B. Microsoft"
            },
            "Lizenzierung": {
                "Lizenztyp": "z.B. OEM (Systembuilder) oder Vollversion (Retail)",
                "Anzahl Lizenzen": "z.B. 1 PC oder 1 Benutzer / 5 Geräte",
                "Medium": "z.B. DVD-ROM, Aktivierungskarte (Key only) oder Download (ESD)"
            },
            "Details": {
                "Kategorie": "z.B. Betriebssystem oder Büroanwendung",
                "Version/Edition": "z.B. 64-bit oder Home & Business 2021",
                "Sprache": "z.B. Deutsch, Multilingual oder Englisch"
            },
            "Systemanforderungen": {
                "Plattform": "Windows, Mac, Android, iOS",
                "Min. Betriebssystem": "z.B. Windows 10 oder macOS 12",
                "Min. Arbeitsspeicher": "z.B. 4 GB",
                "Min. Festplattenspeicher": "z.B. 4 GB"
            }
        }
        """  
        
    elif "wasserkühlung" in cat_lower or "water cooling" in cat_lower or "aio" in cat_lower or "liquid cooler" in cat_lower:
        return base_prompt + """
        Kategorie: Wasserkühlung (AiO / Liquid)
        ERSTELLE EIN HIERARCHISCHES JSON (IT-Scope Datenblatt Style).

        CRITICAL INSTRUCTIONS:
        1. Kompatibilität: Suche explizit nach neuen Sockeln (LGA1851, LGA1700, AM5). Das ist Kaufentscheidend!
        2. Materialien: Unterscheide Kühlerbasis (meist Kupfer) und Radiator (meist Aluminium). Suche auch nach Schlauchmaterial (EPDM).
        3. Lüfter-Specs: Luftdruck (mmH2O), Luftstrom (CFM) und Lager-Typ (Magnetisch, Rifle, etc.).
        4. Maße: Radiator-Abmessungen sind wichtiger als die Pumpen-Maße.

        Benötigte JSON-Struktur:
        {
            "Allgemein": {
                "Produkttyp": "Prozessor-Flüssigkeitskühlsystem",
                "Produktmaterial": "z.B. Aluminium (Radiator), Kupfer (Basis), EPDM (Schläuche)",
                "Packungsinhalt": "z.B. Wärmeleitpaste, Montagekit",
                "Farbe": "z.B. Weiß / Schwarz",
                "Gewicht": "kg"
            },
            "Kühlkörper und Lüfter": {
                "Kompatibel mit": "Liste der Sockel (z.B. LGA1851, LGA1700, Socket AM5)",
                "Radiatormaterial": "z.B. Aluminium",
                "Kühlermaterial": "z.B. Kupfer",
                "Gebläseanzahl": "z.B. 3",
                "Lüfterdurchmesser": "z.B. 120 mm",
                "Lüfterlager": "z.B. Magnetisches Kuppellager oder Rifle Bearing",
                "Drehgeschwindigkeit": "z.B. 500-2000 U/min",
                "Luftstrom": "z.B. 94.87 CFM",
                "Luftdruck": "z.B. 3.91 mm",
                "Geräuschpegel": "dBA",
                "Netzanschluss": "z.B. PWM, 4-polig, ARGB",
                "Merkmale": "z.B. Zero RPM-Lüftermodus, Daisy-Chain, iCUE Support"
            },
            "Abmessungen (Radiator)": {
                 "Breite": "cm (Länge)",
                 "Tiefe": "cm (Breite)",
                 "Höhe": "cm (Dicke)"
            },
            "Herstellergarantie": {
                "Service und Support": "Dauer (z.B. 5 oder 6 Jahre)"
            }
        }
        """
        
    elif "pc-system" in cat_lower or "komplett-pc" in cat_lower or "desktop-pc" in cat_lower or "gaming-pc" in cat_lower:
        return base_prompt + """
        Kategorie: PC-System / Komplett-PC
        ERSTELLE EIN HIERARCHISCHES JSON.

        WICHTIG:
        1. CPU: Modell genau identifizieren (z.B. i9-13900K, Ryzen 7 7800X3D).
        2. GPU: Grafikchip (z.B. RTX 4090, Radeon RX 7900 XTX).
        3. RAM & Speicher: Kapazität (z.B. 32GB DDR5, 2TB SSD).
        4. OS: Windows Version (Home/Pro).

        Benötigte JSON-Struktur:
        {
            "Allgemein": {
                "Gerätetyp": "PC-System",
                "Modell": "Name / Serie",
                "Formfaktor": "z.B. Midi Tower"
            },
            "Hardware": {
                "Prozessor": "z.B. Intel Core i7-13700K",
                "Grafikkarte": "z.B. NVIDIA GeForce RTX 4070 Ti",
                "Arbeitsspeicher": "z.B. 32 GB DDR5",
                "Festplatte": "z.B. 1 TB M.2 SSD",
                "Mainboard-Chipsatz": "z.B. Z790"
            },
            "Software": {
                "Betriebssystem": "z.B. Windows 11 Pro"
            }
        }
        """   
        
    elif "sonstiges" in cat_lower or "zubehör" in cat_lower or "gadget" in cat_lower:
        return base_prompt + """
        Kategorie: Sonstiges / Allgemeines Zubehör
        ERSTELLE EIN HIERARCHISCHES JSON.

        WICHTIG:
        1. Identifiziere, was das Produkt ist (Gerätetyp).
        2. Finde die wichtigste Eigenschaft (z.B. Menge, Größe, Farbe).
        
        Benötigte JSON-Struktur:
        {
            "Allgemein": {
                "Gerätetyp": "z.B. Reinigungsspray, Schraubenset, Mauspad",
                "Modell": "Name",
                "Hersteller": "Name"
            },
            "Eigenschaften": {
                "Merkmal": "z.B. 400ml (Menge) oder M3x10 (Größe)",
                "Farbe": "z.B. Schwarz"
            }
        }
        """  
        
    elif "tastatur_wg34" in cat_lower or "tastatur" in cat_lower and "wg34" in cat_lower:
        return base_prompt + """
        Kategorie: Tastatur (Keyboard)
        ERSTELLE EIN HIERARCHISCHES JSON (IT-Scope Datenblatt Style).

        CRITICAL INSTRUCTIONS:
        1. Layout: Deutsch (QWERTZ), US (QWERTY) oder UK? Wichtigstes Feld!
        2. Typ: Mechanisch (welche Switches? Rot/Blau/Braun/Speed) oder Rubberdome/Membran?
        3. Verbindung: Kabel (Länge?), Wireless (2.4GHz), Bluetooth?
        4. Beleuchtung: RGB, Einfarbig oder Keine?

        Benötigte JSON-Struktur:
        {
            "Allgemein": {
                "Gerätetyp": "Tastatur",
                "Modell": "Name",
                "Farbe": "z.B. Schwarz / Weiß",
                "Lokalisierung und Layout": "z.B. Deutsch (QWERTZ)"
            },
            "Eingabegerät": {
                "Tastaturtechnologie": "z.B. Mechanisch oder Membran (Rubberdome)",
                "Tastenschalter": "z.B. Cherry MX Red / Razer Green",
                "Anschlusstechnik": "z.B. Verkabelt (USB) oder Kabellos",
                "Besonderheiten": "z.B. Nummernblock, Handballenauflage, Spritzwassergeschützt"
            },
            "Konnektivität": {
                "Schnittstelle": "z.B. USB 2.0 / USB-C / Bluetooth",
                "Kabellänge": "z.B. 1.5 m"
            },
            "Abmessungen und Gewicht": {
                "Breite": "cm",
                "Tiefe": "cm",
                "Höhe": "cm",
                "Gewicht": "g"
            },
            "Herstellergarantie": {
                "Service und Support": "Dauer"
            }
        }
        """  
        
    elif "headset_wg36" in cat_lower:
        return base_prompt + """
        Kategorie: Headset (Gaming / Office)
        ERSTELLE EIN HIERARCHISCHES JSON.

        WICHTIG:
        1. Verbindung: Kabelgebunden (USB/Klinke) oder Wireless (Funk/Bluetooth)?
        2. Audio: Stereo, 7.1 Surround oder Spatial Audio?
        3. Bauform: Over-Ear (Ohrumschließend) oder On-Ear?
        4. Mikrofon: Abnehmbar, Klappbar oder Integriert?

        Benötigte JSON-Struktur:
        {
            "Allgemein": {
                "Gerätetyp": "Headset",
                "Modell": "Name",
                "Farbe": "z.B. Schwarz"
            },
            "Technische Daten": {
                "Anschlusstechnik": "z.B. Wireless (2.4 GHz) / Bluetooth oder Verkabelt (USB)",
                "Bauform": "z.B. Ohrumschließend (Over-Ear)",
                "Soundmodus": "z.B. 7.1 Surround Sound oder Stereo"
            },
            "Ausstattung": {
                "Mikrofon": "z.B. Ja, abnehmbar",
                "Beleuchtung": "z.B. RGB"
            }
        }
        """ 
        
        
    elif "streaming" in cat_lower or "capture" in cat_lower or "stream deck" in cat_lower or "elgato" in cat_lower:
        return base_prompt + """
        Kategorie: Streaming Equipment (Capture Card, Stream Deck, Licht)
        ERSTELLE EIN HIERARCHISCHES JSON.

        WICHTIG:
        1. Gerätetyp: Capture Card, Stream Controller, Green Screen oder Licht?
        2. Specs (Video): Max. Auflösung & FPS (z.B. 4K60, 1080p60) - nur bei Capture Cards.
        3. Specs (Controller): Anzahl der Tasten (z.B. 15 Tasten) - nur bei Stream Decks.
        4. Anschluss: USB, PCIe, HDMI?

        Benötigte JSON-Struktur:
        {
            "Allgemein": {
                "Gerätetyp": "z.B. Capture Card oder Stream Deck",
                "Modell": "Name",
                "Hersteller": "z.B. Elgato"
            },
            "Technische Daten": {
                "Auflösung (Video)": "z.B. 4K60 HDR oder 1080p60 (bei Capture Cards)",
                "Anzahl Tasten": "z.B. 15 LCD-Tasten (bei Decks)",
                "Schnittstelle": "z.B. USB 3.0, PCIe x4"
            },
            "Ausstattung": {
                "Funktionen": "z.B. Passthrough, Multi-App Control"
            }
        }
        """ 
        
    elif "lautsprecher" in cat_lower or "speaker" in cat_lower or "soundbar" in cat_lower or "boxen" in cat_lower:
        return base_prompt + """
        Kategorie: Lautsprecher / Soundsystem
        ERSTELLE EIN HIERARCHISCHES JSON.

        WICHTIG:
        1. System: 2.0 (Stereo), 2.1 (mit Subwoofer), 5.1 (Surround) oder Soundbar?
        2. Verbindung: Bluetooth, USB, 3.5mm Klinke (AUX) oder Optisch?
        3. Leistung: Gesamtleistung in Watt (RMS).
        
        Benötigte JSON-Struktur:
        {
            "Allgemein": {
                "Gerätetyp": "Lautsprecher",
                "Modell": "Name",
                "Farbe": "z.B. Schwarz"
            },
            "Technische Daten": {
                "Kanäle": "z.B. 2.0, 2.1 oder 5.1",
                "Gesamtleistung": "z.B. 40 Watt (RMS)",
                "Frequenzbereich": "z.B. 55 Hz - 20 kHz"
            },
            "Konnektivität": {
                "Schnittstellen": "z.B. Bluetooth 5.0, 3.5mm Klinke, USB",
                "Stromversorgung": "z.B. Netzteil oder USB-Powered"
            }
        }
        """  
        
    elif "mauspad_wg39" in cat_lower:
        return base_prompt + """
        Kategorie: Mauspad / Deskmat
        ERSTELLE EIN HIERARCHISCHES JSON.

        WICHTIG:
        1. Größe: Abmessungen in mm/cm (z.B. 900x400mm) oder Format (L, XL, XXL, Extended).
        2. Material: Stoff (Textil/Soft) oder Hartplastik (Hard)?
        3. Features: Genähte Ränder, RGB-Beleuchtung, Qi-Charging?

        Benötigte JSON-Struktur:
        {
            "Allgemein": {
                "Gerätetyp": "Mauspad",
                "Modell": "Name",
                "Farbe": "z.B. Schwarz"
            },
            "Technische Daten": {
                "Abmessungen": "z.B. 900 x 400 x 4 mm",
                "Größenklasse": "z.B. XXL / Extended",
                "Material": "z.B. Stoff / Textil oder Hartplastik",
                "Oberfläche": "z.B. Speed oder Control (falls angegeben)"
            },
            "Ausstattung": {
                "Besonderheiten": "z.B. Anti-Rutsch-Boden, Vernähte Ränder, RGB-Beleuchtung"
            }
        }
        """  
        
    elif "desktop_set_wg40" in cat_lower or "desktop set" in cat_lower or "tastatur-und-maus" in cat_lower or "combo" in cat_lower:
        return base_prompt + """
        Kategorie: Maus-Tastatur-Set (Desktop Set / Combo)
        ERSTELLE EIN HIERARCHISCHES JSON (IT-Scope Datenblatt Style).

        CRITICAL INSTRUCTIONS:
        1. Layout: Deutsch (QWERTZ) oder anderes?
        2. Verbindung: Wireless (Funk/Bluetooth) oder Kabelgebunden?
        3. Inhalt: Details zu Maus (DPI) UND Tastatur (Switches/Layout) suchen.

        Benötigte JSON-Struktur:
        {
            "Allgemein": {
                "Gerätetyp": "Tastatur-und-Maus-Set",
                "Modell": "Name",
                "Farbe": "z.B. Pale Gray / Schwarz",
                "Schnittstelle": "z.B. 2.4 GHz Wireless / Bluetooth"
            },
            "Tastatur": {
                "Layout": "z.B. Deutsch (QWERTZ)",
                "Tastenschalter": "z.B. CHERRY SX Schere",
                "Besonderheiten": "z.B. Nummernblock, Handballenauflage",
                "Batterie": "z.B. 2x AA"
            },
            "Maus": {
                "Typ": "z.B. Optisch / Laser",
                "Bewegungsauflösung": "z.B. 2400 dpi (umschaltbar)",
                "Anzahl Tasten": "Anzahl",
                "Batterie": "z.B. 1x AA"
            },
            "Verschiedenes": {
                "Zubehör im Lieferumfang": "z.B. Batterien, Nano-Empfänger",
                "MTBF": "z.B. 80.000 Stunden"
            },
            "Herstellergarantie": {
                "Service und Support": "Dauer"
            }
        }
        """
        
    elif "service" in cat_lower or "garantie" in cat_lower or "warranty" in cat_lower or "dienstleistung" in cat_lower or "care pack" in cat_lower:
        return base_prompt + """
        Kategorie: Service / Dienstleistung
        ERSTELLE EIN HIERARCHISCHES JSON.

        WICHTIG:
        1. Art des Service: Garantieerweiterung, Montage, Prüfung, Versicherung?
        2. Dauer: Zeitspanne (z.B. 3 Jahre, 12 Monate).
        3. Umfang: Vor-Ort (On-Site), Bring-In, Pick-Up?

        Benötigte JSON-Struktur:
        {
            "Allgemein": {
                "Dienstleistungstyp": "z.B. Garantieerweiterung",
                "Bezeichnung": "Name des Service",
                "Dauer": "z.B. 3 Jahre (falls zutreffend)"
            },
            "Details": {
                "Art": "z.B. Vor-Ort-Service, Pick-Up & Return oder Next Business Day",
                "Abdeckung": "z.B. Hardware-Reparatur"
            }
        }
        """
        
    elif "usb-stick" in cat_lower or "flash drive" in cat_lower or "thumb drive" in cat_lower:
        return base_prompt + """
        Kategorie: USB-Stick (Flash Drive)
        ERSTELLE EIN HIERARCHISCHES JSON.

        WICHTIG:
        1. Kapazität: Speichergröße (z.B. 64 GB, 128 GB).
        2. Standard: USB 2.0, 3.0, 3.1, 3.2 Gen 1?
        3. Anschluss: USB-A, USB-C oder Dual (beides)?

        Benötigte JSON-Struktur:
        {
            "Allgemein": {
                "Gerätetyp": "USB-Stick",
                "Modell": "Name",
                "Farbe": "z.B. Schwarz"
            },
            "Technische Daten": {
                "Kapazität": "z.B. 128 GB",
                "Schnittstelle": "z.B. USB 3.2 Gen 1 (USB-A)",
                "Lesegeschwindigkeit": "z.B. 100 MB/s (falls verfügbar)"
            },
            "Besonderheiten": {
                "Verschlüsselung": "Ja / Nein",
                "Bauform": "z.B. Slider / Kappe / Mini"
            }
        }
        """                                          
             
    #Fallback, neu Kategorien werden genau hier drüber eingefügt
    else:
        return base_prompt + """
        Identifiziere die Kategorie selbst.
        Erstelle ein sinnvolles, hierarchisches JSON.
        """