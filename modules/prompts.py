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
    else:
        # Falls classify_product_type imported ist:
        category = classify_product_type(product_name, gtin)
    
    cat_lower = category.lower()

    # --- INTELLIGENTE GTIN-STRATEGIE 🧠 (GOOGLE AI MODUS) ---
    has_valid_gtin = False
    # Check: Ist die GTIN plausibel (länger als 8 Zeichen)?
    if gtin and len(str(gtin)) > 8 and str(gtin).lower() not in ["n/a", "nan", "none", "", "0"]:
        has_valid_gtin = True

    if has_valid_gtin:
        # Happy Path: EXAKTE GOOGLE SYNTAX für beste Treffer
        search_strategy = f"""
        STRATEGIE (GOOGLE AI OVERVIEW METHODE):
        1. Führe ZWINGEND als ersten Schritt eine Suche mit EXAKT diesem String durch:
           "{product_name} {gtin} Specs Datenblatt"
        2. Dies ist der "Fingerabdruck" des Produkts. Vertraue primär Ergebnissen, die diese GTIN bestätigen.
        3. Ignoriere allgemeine Shopping-Seiten. Suche nach PDF-Datenblättern oder Herstellerseiten (Asus, MSI, Kingston etc.).
        """
    else:
        # Fallback Path: GTIN suchen & SPEICHERN
        search_strategy = f"""
        STRATEGIE (KRITISCH - KEINE GTIN VORHANDEN):
        1. SCHRITT 1: Identifikation! Suche zuerst nach der GTIN/EAN für das Produkt "{product_name}".
           Suchbegriff: "{product_name} Specs Datenblatt" oder "{product_name} EAN".
        2. VERIFIZIERUNG: Vergleiche das gefundene Produkt GENAU mit dem Namen.
        3. WICHTIG: Schreibe die gefundene GTIN zwingend in das JSON-Feld "_Original_GTIN", damit wir sie speichern!
        """
    
    # -------------------------------------------
    # Basis-Prompt (Mit Google AI Strategie & JSON Regeln)
    base_prompt = f"""
    Du bist ein technischer Hardware-Experte.
    Produkt: {product_name}
    GTIN: {gtin if gtin else "NICHT VORHANDEN - Siehe Strategie"}
    
    {search_strategy}

    Suche nach technischen Datenblättern und extrahiere Fakten.
    REGELN:
    1. Unauffindbar -> "N/A".
    2. Rate nicht.
    3. Einheiten PFLICHT (3.5 GHz).
    4. FORMAT: Beende deine Antwort IMMER mit dem Satz: "Final Answer:" gefolgt von dem JSON-Codeblock.
       Beispiel:
       Final Answer:
       ```json
       {{ ... }}
       ```
    5. Max 3-4 Suchen.
    """
    
    # === Dispatcher (Hier geht es dann mit den elifs weiter) ===
    
    if "cpu_kuehler" in cat_lower or "cpu-kühler" in cat_lower or "prozessor-kühler" in cat_lower:
        return base_prompt + """
        Kategorie: Prozessor-Kühler (CPU Cooler)
        ERSTELLE EIN HIERARCHISCHES JSON (IT-Scope Datenblatt Style).

        CRITICAL INSTRUCTIONS:
        1. KOMPATIBILITÄT: Das ist das Wichtigste! Gib eine SAUBERE LISTE (Array) aller Sockel zurück.
           Beispiel: ["LGA1700", "AM5", "AM4", "LGA1200", "LGA115x"].
        2. MAßE: Die Gesamthöhe (mit Lüfter!) ist entscheidend für Gehäuse.
        3. LÜFTER-SPECS: Suche nach Luftdruck (mmH2O), Luftstrom (CFM/m³/h) und Lautstärke.
        4. STROM: Versuche Nennspannung (V), Nennstrom (A) und Verbrauch (W) zu finden.

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
                "Kompatibel mit": ["Sockel A", "Sockel B"],
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
                "Nennstrom": "A (z.B. 0.2 A)",
                "Energieverbrauch": "Watt (z.B. 2.4 W)",
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
        1. ANSCHLÜSSE: Zähle EXAKT! "Angaben zu Ausgangsleistungsanschlüssen" muss eine Liste sein (z.B. "1 x 24-pin", "2 x 12VHPWR", "6 x PCIe 8-pin").
        2. 12VHPWR CHECK: Suche explizit nach "12VHPWR", "PCIe 5.0", "16-pin" Kabeln (wichtig für RTX 40er Karten).
        3. STROMSTÄRKEN: Fülle "Ausgangsstrom" detailliert (+3.3V, +5V, +12V Single/Multi-Rail).
        4. MODULARITÄT: "Voll-modular", "Teil-modular" oder "Nicht modular"?
        5. ZERTIFIZIERUNG: 80 PLUS (Gold, Platinum, Titanium?).

        Benötigte JSON-Struktur:
        {
            "Allgemein": {
                "Gerätetyp": "Netzteil - aktive Power Factor Correction (PFC) - intern",
                "Spezifikationseinhaltung": "z.B. ATX12V 3.0 / EPS12V 2.92",
                "Netzteil-Formfaktor": "z.B. ATX",
                "Farbe": "z.B. Schwarz",
                "Lokalisierung": "z.B. Europa"
            },
            "Stromversorgungsgerät": {
                "Eingangsspannung": "z.B. Wechselstrom 100-240 V",
                "Nötige Frequenz": "z.B. 50 - 60 Hz",
                "Angaben zu Ausgangsleistungsanschlüssen": "Liste (z.B. 1x 24-Pin ATX, 1x 16-Pin 12VHPWR, 4x 8-Pin PCIe)",
                "Ausgangsspannung": "z.B. +3.3, +5, ±12 V",
                "Leistungskapazität": "Wattzahl (z.B. 850 Watt)",
                "Ausgangsstrom": "Liste (z.B. +3.3V - 20 A ¦ +5V - 20 A ¦ +12V - 70 A)",
                "Effizienz": "z.B. 90% (80 PLUS Gold)",
                "Modulare Kabelverwaltung": "Ja / Nein",
                "80-PLUS-Zertifizierung": "z.B. 80 PLUS Gold"
            },
            "Verschiedenes": {
                "Besonderheiten": "Liste (z.B. OVP, OCP, OTP, Zero RPM Mode, Lüfterlager)",
                "Zubehör im Lieferumfang": "z.B. Kabelbinder, Schrauben",
                "Kühlsystem": "z.B. 135-mm-Lüfter",
                "MTBF": "z.B. 100.000 Stunden",
                "Kennzeichnung": "z.B. TUV, CB, CE"
            },
            "Abmessungen und Gewicht": {
                "Breite": "cm",
                "Tiefe": "cm",
                "Höhe": "cm",
                "Gewicht": "kg"
            },
            "Herstellergarantie": {
                "Service und Support": "Dauer (z.B. 10 Jahre)"
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
        2. Verpackung: "Box" (Retail, oft mit Kühler) vs. "OEM/Tray" (Nur CPU). Suche nach "WOF" (Without Fan) oder "MPK".
        3. Cache: Nenne L2 und L3 Cache separat oder als "Cache-Speicher-Details".
        4. Grafik: Prüfe auf integrierte Grafik (iGPU). 
           - Intel 'F'-Modelle (z.B. 14900F) haben KEINE Grafik! -> "Eingebaute Grafikadapter": "Nein".
           - Ryzen 7000/9000 haben oft eine "Radeon Graphics" iGPU (klein).

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
                "Typ / Formfaktor": "Voller Name",
                "Anz. der Kerne": "Gesamt + Split (z.B. 24 Kerne (8P + 16E))",
                "Anz. der Threads": "Anzahl",
                "Taktfrequenz": "Basis (z.B. 2 GHz (P-Kern) / 1.5 GHz (E-Kern))",
                "Max. Turbo-Taktfrequenz": "Turbo (z.B. 5.8 GHz (P-Kern))",
                "Cache-Speicher": "Gesamt (z.B. 36 MB)",
                "Cache-Speicher-Details": "Details (z.B. Smart Cache - 36 MB ¦ L2 - 32 MB)",
                "Thermal Design Power (TDP)": "Basis-Watt (z.B. 65 W)",
                "Maximale Turbo-Leistung": "Max-Watt (z.B. 219 W)",
                "Herstellungsprozess": "z.B. 10 nm oder 5 nm",
                "PCI Express Revision": "z.B. 4.0/5.0",
                "Anz. PCI Express Lanes": "Anzahl"
            },
            "Grafik": {
                "Eingebaute Grafikadapter": "Ja / Nein",
                "On-Board Grafikadaptermodell": "Modell (z.B. Intel UHD 770 oder AMD Radeon Graphics)",
                "On-Board Grafikadapter Basisfrequenz": "MHz",
                "Maximale dynamische Frequenz der On-Board Grafikadapter": "MHz"
            },
            "Speicher": {
                "Maximaler interner Speicher, vom Prozessor unterstützt": "z.B. 128 GB",
                "Speichertaktraten, vom Prozessor unterstützt": "z.B. DDR5-5600",
                "Speicherkanäle": "z.B. Dual-channel",
                "ECC": "Ja / Nein"
            },
            "Architektur-Merkmale": {
                "Besonderheiten": "Liste (z.B. Hyper-Threading, DL Boost, AVX2, EXPO, Intel Thread Director)"
            },
            "Verschiedenes": {
                "Verpackung": "z.B. OEM/Tray oder Box",
                "Zubehör im Lieferumfang": "z.B. Kühler (nur wenn Box)"
            },
            "Abmessungen & Gewicht (Transport)": {
                "Transportbreite": "cm",
                "Transporttiefe": "cm"
            }
        }
        """

    elif "grafikkarte" in cat_lower or "gpu" in cat_lower or "videokarte" in cat_lower:
        return base_prompt + """
        Kategorie: Grafikkarte (GPU)
        ERSTELLE EIN HIERARCHISCHES JSON (IT-Scope Datenblatt Style).

        CRITICAL INSTRUCTIONS:
        1. STROMANSCHLUSS (WICHTIG):
           - NVIDIA RTX 4000er Serie: Meist "1x 16-Pin (12VHPWR)".
           - AMD Radeon: Meist "2x 8-Pin PCIe" (AMD nutzt selten 12VHPWR!).
           - SCHREIBE NIEMALS "ODER"! Entscheide dich basierend auf dem Modell.
        2. MAßE-LOGIK (IT-Scope Standard):
           - "Tiefe": Die LÄNGE der Karte (z.B. 300 mm).
           - "Breite": Die HÖHE der Karte (vom PCIe-Slot zur Seitenwand, z.B. 130 mm).
           - "Höhe": Die DICKE der Karte (Slot-Belegung, z.B. 50 mm / 2.5 Slots).
        3. KERNE:
           - Nvidia = "CUDA-Kerne".
           - AMD = "Stream Prozessoren".

        Benötigte JSON-Struktur:
        {
            "Allgemein": {
                "Gerätetyp": "Grafikkarten",
                "Grafikprozessor": "Voller Name (z.B. NVIDIA GeForce RTX 4070 Ti SUPER)",
                "Bustyp": "z.B. PCI Express 4.0 x16",
                "Boost-Takt": "MHz",
                "Stream Prozessoren": "Anzahl (AMD) / CUDA-Kerne (Nvidia)",
                "Max Auflösung": "z.B. 7680 x 4320",
                "Anzahl der max. unterstützten Bildschirme": "Anzahl (z.B. 4)",
                "Schnittstellendetails": "Liste (z.B. 3 x DisplayPort 1.4a, 1 x HDMI 2.1a)",
                "API-Unterstützung": "z.B. DirectX 12 Ultimate, OpenGL 4.6",
                "Besonderheiten": "z.B. Dual BIOS, RGB Fusion, 0dB Technology"
            },
            "Speicher": {
                "Grösse": "z.B. 16 GB",
                "Technologie": "z.B. GDDR6X",
                "Speichergeschwindigkeit": "z.B. 21 Gbps",
                "Busbreite": "z.B. 256-bit"
            },
            "Systemanforderungen": {
                "Erforderliche Leistungsversorgung": "Empfohlenes Netzteil in Watt (z.B. 750 W)",
                "Zusätzliche Anforderungen": "Exakter Stromstecker! (z.B. 1x 16-Pin (12VHPWR))"
            },
            "Verschiedenes": {
                "Leistungsaufnahme im Betrieb": "TGP/TBP in Watt (z.B. 285 W)",
                "Zubehör im Lieferumfang": "Liste",
                "Breite": "mm (PCB-Höhe)",
                "Tiefe": "mm (Länge)",
                "Höhe": "mm (Dicke/Slots)",
                "Gewicht": "kg"
            },
             "Herstellergarantie": {
                "Service und Support": "Dauer"
            }
        }
        """

    elif "mainboard" in cat_lower or "motherboard" in cat_lower:
        # Wir überschreiben die Strategie für Mainboards, weil wir das HANDBUCH brauchen!
        mb_strategy = f"""
        STRATEGIE (MAINBOARD SPEZIAL):
        1. BASIS: Suche nach "{product_name} {gtin} Specs".
        2. ENTSCHEIDEND: Suche nach "{product_name} manual pdf" oder "Handbuch download".
           (Nur im Handbuch/Manual findest du die exakte Anzahl der internen USB-Header und Lüfter-Anschlüsse!)
        3. FALLE VERMEIDEN: Achte auf Revisionen (Rev 1.0 vs 1.1) – nimm im Zweifel die neueste.
        """

        return base_prompt + f"""
        {mb_strategy}
        
        Kategorie: Mainboard (Motherboard)
        ERSTELLE EIN HIERARCHISCHES JSON (IT-Scope Datenblatt Style).

        CRITICAL INSTRUCTIONS (ANTI-HALLUCINATION & PRECISION):
        1. SCHNITTSTELLEN-TRENNUNG (WICHTIG!): 
           - "Schnittstellen (Rückseite)" sind NUR die Ports am I/O-Panel hinten.
           - "Interne Schnittstellen" sind NUR die Pfostenstecker/Header AUF dem Board.
           - VERMISCHE DIESE NIEMALS!
        2. PCIe SLOTS: Unterscheide elektrisch! "PCIe 4.0 x16 (x4 mode)" ist nicht dasselbe wie "x16".
        3. RAM TAKT: Liste ALLE unterstützten OC-Frequenzen auf (z.B. "7200+(OC), 7000(OC)...").
        4. CHIPSATZ: Achte auf Suffixe! "X670" != "X670E".
        5. WIFI/LAN: Suche explizit nach der Version (Wi-Fi 6E vs Wi-Fi 7).

        Benötigte JSON-Struktur:
        {{
            "Allgemein": {{
                "Produkttyp": "z.B. Motherboard - ATX",
                "Chipsatz": "Exakter Name (z.B. AMD X670E)",
                "Prozessorsockel": "z.B. Socket AM5",
                "Kompatible Prozessoren": "z.B. Unterstützt AMD Ryzen 9000 Series",
                "Max. Anz. Prozessoren": "1"
            }},
            "Unterstützter RAM": {{
                "Max. Größe": "z.B. 192 GB",
                "Technologie": "z.B. DDR5",
                "Bustakt": "VOLLE LISTE (z.B. 8000+(OC)... 4800 MHz)",
                "Besonderheiten": "z.B. Dual Channel, EXPO, XMP",
                "Registriert oder gepuffert": "Ungepuffert"
            }},
            "Audio": {{
                "Typ": "z.B. HD Audio (8-Kanal)",
                "Audio Codec": "z.B. Realtek ALC4080"
            }},
            "LAN": {{
                "Netzwerkschnittstellen": "z.B. 2.5 Gigabit Ethernet, Wi-Fi 7, Bluetooth 5.4"
            }},
            "Erweiterung/Konnektivität": {{
                "Erweiterungssteckplätze": "Detaillierte Liste (z.B. 1x PCIe 5.0 x16)",
                "Speicherschnittstellen": "Liste (z.B. 4x SATA-600, 4x M.2)",
                "Schnittstellen (Rückseite)": "EXAKTE LISTE I/O Panel (z.B. 1x HDMI, 2x USB-C...)",
                "Interne Schnittstellen": "Header auf Board (z.B. 1x USB-C Header, 2x USB 2.0 Header)",
                "Stromanschlüsse": "z.B. 1x 24-Pin ATX, 2x 8-Pin 12V"
            }},
            "Besonderheiten": {{
                "BIOS-Typ": "z.B. AMI UEFI",
                "Hardwarefeatures": "Liste (z.B. M.2 Thermal Guard)"
            }},
            "Verschiedenes": {{
                "Zubehör im Lieferumfang": "Liste",
                "Breite": "cm",
                "Tiefe": "cm"
            }},
             "Herstellergarantie": {{
                "Service und Support": "Dauer"
            }}
        }}
        """

    if "arbeitsspeicher" in cat_lower or "ram" in cat_lower or "memory" in cat_lower:
        return base_prompt + """
         Kategorie: Arbeitsspeicher (RAM)
         ERSTELLE EIN HIERARCHISCHES JSON (IT-Scope Datenblatt Style).

         !!! CRITICAL RULES (STRICT ADHERENCE REQUIRED) !!!
         1. EXAKTHEIT VOR POPULARITÄT:
         - Prüfe ZWINGEND die Herstellernummer (SKU/GTIN).
         - Beispiel: G.Skill gibt es als CL16 und CL18. Wenn du unsicher bist, nimm die konservativeren (langsameren) Timings.
    
         2. PROFILE (XMP vs. EXPO) - NICHT RATEN:
         - Schreibe "AMD EXPO" NUR, wenn "EXPO", "AMD Ready" oder "Ryzen Tuned" explizit genannt wird.
         - Schreibe "Intel XMP" NUR, wenn "XMP" oder "Intel Ready" explizit genannt wird.
         - Schreibe BEIDES nur, wenn das Datenblatt explizit "Dual Profile" oder beides erwähnt.
         - Im Zweifel: Wenn "AMD Edition" im Titel steht, entferne "Intel XMP".

         3. DDR5 SPEZIALREGEL (ECC):
         - Wenn Technologie == "DDR5", dann ist "Datenintegritätsprüfung" IMMER "On-Die ECC" (nicht "Non-ECC").
         - Nur bei Server-RAM (Registered/Buffered) schreibe "ECC".

         4. KAPAZITÄTS-FORMATIERUNG:
         - Feld "Kapazität": NUR die Gesamtsumme (z.B. "32 GB"). KEINE Formeln wie "16GB + 16GB".
         - Die Aufteilung kommt NUR in das Feld "Modulkonfiguration".

         5. TECHNISCHE DETAILS:
         - Spannung: Suche präzise (DDR4 oft 1.35V, DDR5 oft 1.1V, 1.25V oder 1.35V/1.4V bei OC).
         - Timings: Versuche die Kette zu finden (z.B. 30-38-38-96).

         Benötigte JSON-Struktur:
        {
          "Allgemein": {
            "Kapazität": "Nur Gesamtwert (z.B. '32 GB')",
            "Erweiterungstyp": "Generisch",
            "Breite": "N/A",
            "Tiefe": "N/A",
            "Höhe": "Wenn verfügbar (z.B. '34.9 mm')"
        },
        "Speicher": {
            "Typ": "DRAM",
            "Technologie": "DDR4 SDRAM oder DDR5 SDRAM",
            "Formfaktor": "DIMM 288-PIN (Desktop) oder SO-DIMM (Laptop)",
            "Geschwindigkeit": "Geschwindigkeit in MT/s oder MHz (z.B. '6000 MT/s')",
            "Latenzzeiten": "CAS Latency + Timings (z.B. 'CL30 (30-36-36)')",
            "Datenintegritätsprüfung": "Bei DDR4: 'Non-ECC', bei DDR5: 'On-Die ECC'",
            "Besonderheiten": "Liste EXAKT auf (XMP 3.0, EXPO, RGB, Heatspreader Farbe)",
            "Modulkonfiguration": "Anzahl x Einzelgröße (z.B. '2 x 16 GB')",
            "Chip-Organisation": "N/A oder 'x8' / 'x16'",
            "Spannung": "Exakter Wert (z.B. '1.35 V')"
        },
        "Verschiedenes": {
            "Farbe": "Farbe des Heatspreaders",
            "Produktzertifizierungen": "z.B. RoHS"
        },
         "Herstellergarantie": {
            "Service und Support": "Dauer (z.B. Begrenzte lebenslange Garantie)"
        }
    }
    """

    elif "speicher" in cat_lower or "ssd" in cat_lower or "hdd" in cat_lower or "festplatte" in cat_lower or "hard drive" in cat_lower:
        return base_prompt + """
        Kategorie: Speicher (SSD / HDD)
        ERSTELLE EIN HIERARCHISCHES JSON (IT-Scope Datenblatt Style).

        CRITICAL INSTRUCTIONS:
        1. GESCHWINDIGKEIT: Lesen/Schreiben in MB/s (z.B. 7450 MB/s).
        2. SCHNITTSTELLE: Exakt! "Serial ATA III", "PCI Express 4.0 x4", "SAS".
        3. FORMFAKTOR: "M.2 2280", "2.5\"", "3.5\"".
        4. HALTBARKEIT: Suche nach "TBW-Bewertung" (Total Bytes Written) und "MTBF".
        5. FEATURE: "NVMe": Ja/Nein.

        Benötigte JSON-Struktur:
        {
            "Merkmale": {
                "Gerätetyp": "z.B. Solid State Drive (SSD) oder Festplatte (HDD)",
                "SSD Speicherkapazität": "z.B. 1000 GB",
                "SSD-Formfaktor": "z.B. M.2 2280 oder 2.5\"",
                "Schnittstelle": "z.B. Serial ATA III oder PCI Express 4.0 x4",
                "NVMe": "Ja / Nein",
                "Komponente für": "PC/notebook",
                "Speichertyp": "z.B. 3D NAND, V-NAND, TLC",
                "Datenübertragungsrate": "z.B. 6 Gbit/s",
                "Lesegeschwindigkeit": "z.B. 560 MB/s",
                "Schreibgeschwindigkeit": "z.B. 530 MB/s",
                "S.M.A.R.T. Unterstützung": "Ja / Nein",
                "TRIM-Unterstützung": "Ja / Nein",
                "TBW-Bewertung": "z.B. 600",
                "Mittlere Betriebsdauer zwischen Ausfällen (MTBF)": "z.B. 1.500.000 h"
            },
            "Sicherheit": {
                "Hardwareverschlüsselung": "Ja / Nein",
                "Unterstützte Sicherheitsalgorithmen": "z.B. 256-bit AES"
            },
            "Leistung": {
                "Stromverbrauch (max.)": "Watt",
                "Stromverbrauch (durchschnittl.)": "Watt"
            },
            "Gewicht und Abmessungen": {
                "Breite": "mm",
                "Tiefe": "mm",
                "Höhe": "mm",
                "Gewicht": "g"
            },
            "Betriebsbedingungen": {
                "Temperaturbereich in Betrieb": "z.B. 0 - 70 °C",
                "Stoßfest (in Betrieb)": "z.B. 1500 G"
            },
            "Verpackungsdaten": {
                "Verpackungsart": "z.B. Box"
            }
        }
        """
        
    elif "monitor" in cat_lower or "tft" in cat_lower or "display" in cat_lower or "bildschirm" in cat_lower:
        return base_prompt + """
        Kategorie: Monitor (TFT / Display)
        ERSTELLE EIN HIERARCHISCHES JSON (IT-Scope Datenblatt Style).

        CRITICAL INSTRUCTIONS:
        1. AUFLÖSUNG: Nenne die Auflösung UND die Bildwiederholrate (Hz). Wenn möglich pro Anschluss (z.B. "DP: 165Hz, HDMI: 144Hz").
        2. PANEL: Welcher Typ? (IPS, VA, TN, OLED, QD-OLED, Mini-LED).
        3. ANSCHLÜSSE: Sei extrem präzise! "USB-C mit 65W PD" ist besser als nur "USB-C".
        4. FARBE: Farbraumabdeckung (sRGB, DCI-P3, Adobe RGB) als Liste oder Text.
        5. ERGONOMIE: Höhenverstellbar? Pivot (hochkant)? VESA?

        Benötigte JSON-Struktur:
        {
            "Allgemein": {
                "Gerätetyp": "z.B. LED-hintergrundbeleuchteter LCD-Monitor",
                "Energie Effizienzklasse": "z.B. Klasse F",
                "Energieklasse (HDR)": "z.B. Klasse G",
                "Diagonalabmessung": "z.B. 27 Zoll (69 cm)",
                "Geschwungener Bildschirm": "Ja (1500R) / Nein",
                "Panel-Typ": "z.B. IPS, VA, Rapid VA, QD-OLED",
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
                "Besonderheiten": "z.B. Flicker-Free, Low Blue Light, AMD FreeSync Premium, G-Sync Compatible"
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

    elif "gehäuse" in cat_lower or "pc case" in cat_lower or "tower" in cat_lower:
        return base_prompt + """
        Kategorie: Gehäuse (PC Case)
        ERSTELLE EIN HIERARCHISCHES JSON (IT-Scope Datenblatt Style).

        CRITICAL INSTRUCTIONS (ANTI-HALLUCINATION):
        1. VERPACKUNG vs. PRODUKT: Unterscheide strikt zwischen "Package Dimensions" und "Product Dimensions". Nimm IMMER die kleineren Werte!
        2. GEWICHT: Suche nach "Net Weight" (Nettogewicht). Ignoriere "Gross Weight".
        3. FORMAT-CHECK: Ein "Micro-ATX" Gehäuse unterstützt KEIN Standard-ATX Mainboard!
        4. KÜHLUNG & RADIATOREN: Suche nach unterstützten Lüftergrößen (120mm, 140mm) und Radiatorgrößen (240mm, 360mm). Schreib nicht nur "Vorne", sondern "Vorne: bis zu 3x 120mm".
        5. MAßE-LOGIK: Bei Tower-Gehäusen ist die HÖHE (Height) meist ähnlich zur TIEFE (Depth/Length), aber die BREITE (Width) ist deutlich kleiner (meist 200-250mm).

        Benötigte JSON-Struktur:
        {
            "Allgemein": {
                "Formfaktor": "z.B. Midi Tower, Mini Tower, MicroATX Case",
                "Max. Mainboard-Größe": "Der größte unterstützte Standard (z.B. ATX, E-ATX)",
                "Unterstützte Motherboards": "Liste der Formate (z.B. ATX, microATX, Mini-ITX)",
                "Seitenplatte mit Fenster": "Ja / Nein",
                "Seitliches Plattenmaterial mit Fenster": "z.B. Gehärtetes Glas (Tempered Glass), Acryl",
                "Produktmaterial": "z.B. Stahl, ABS Kunststoff, Mesh",
                "Farbe": "z.B. Schwarz, Weiß",
                "Anzahl interner Einbauschächte": "Detailliert! z.B. 2 x 3.5 Zoll, 3 x 2.5 Zoll (NICHT 2/2 schreiben!)",
                "Kühlsystem": "Details zu Lüftern/Radiatoren. z.B. 'Vorne: 3x 120mm, Oben: 2x 140mm Support'",
                "Max. Höhe des CPU-Kühlers": "mm (Exakter Wert!)",
                "Maximale Länge Videokarte": "mm",
                "Maximallänge der Stromversorgung": "mm",
                "Systemgehäuse-Merkmale": "z.B. Kabelmanagement, Staubfilter, Airflow-Front"
            },
            "Erweiterung/Konnektivität": {
                "Erweiterungseinschübe": "z.B. 2 (gesamt) / 2 (frei) x intern - 2.5 Zoll",
                "Erweiterungssteckplätze": "Anzahl (z.B. 7)",
                "Schnittstellen": "Exakte USB Versionen! z.B. 1x USB-C 3.2 Gen 2, 2x USB 3.0, Audio In/Out"
            },
            "Stromversorgung": {
                "Stromversorgungsgerät": "Meist 'Ohne Netzteil'",
                "Spezifikationseinhaltung": "z.B. ATX / PS2"
            },
            "Abmessungen und Gewicht": {
                "Breite": "mm",
                "Tiefe": "mm (Länge)",
                "Höhe": "mm",
                "Gewicht": "kg"
            },
            "Herstellergarantie": {
                "Service und Support": "Dauer (z.B. 3 Jahre)"
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
        
    elif "wasserkühlung" in cat_lower or "water cooling" in cat_lower or "aio" in cat_lower or "liquid cooler" in cat_lower or "liquid" in cat_lower:
        return base_prompt + """
        Kategorie: Wasserkühlung (AiO / Liquid Cooler)
        ERSTELLE EIN HIERARCHISCHES JSON (IT-Scope Datenblatt Style).

        CRITICAL INSTRUCTIONS:
        1. RADIATOR: Maße sind kritisch! Nutze Key "Kühlerabmessungen" (z.B. 394 x 120 x 27 mm).
        2. LÜFTER: Anzahl (Key: "Gebläseanzahl").
        3. KOMPATIBILITÄT: Liste der Sockel als ARRAY ["LGA1700", "AM5"].
        4. CPU-FAMILIEN: Liste unterstützte Serien unter "Prozessorkompatibilität" (z.B. Core i9, Ryzen).

        Benötigte JSON-Struktur:
        {
            "Allgemein": {
                "Produkttyp": "Prozessor-Flüssigkeitskühlsystem",
                "Gewicht": "g oder kg",
                "Farbe": "z.B. Schwarz",
                "Breite": "cm (Radiator)",
                "Tiefe": "cm",
                "Höhe": "cm"
            },
            "Kühlkörper und Lüfter": {
                "Kompatibel mit": ["Sockel A", "Sockel B"],
                "Prozessorkompatibilität": "Liste (z.B. Core i9, Core i7, Ryzen)",
                "Kühlermaterial": "z.B. Kupfer",
                "Radiatormaterial": "z.B. Aluminium",
                "Kühlerabmessungen": "z.B. 276 mm x 120 mm x 27 mm",
                "Gebläseanzahl": "z.B. 2",
                "Lüfterdurchmesser": "z.B. 120 mm",
                "Gebläsehöhe": "z.B. 25 mm",
                "Lüfterlager": "z.B. Magnetisches Kuppellager",
                "Drehgeschwindigkeit": "z.B. 300 - 2100 U/min",
                "Luftstrom": "z.B. 10.4-73.5 cfm",
                "Luftdruck": "z.B. 0.12-4.33 mm",
                "Geräuschpegel": "z.B. 10 - 36 dBA",
                "Netzanschluss": "z.B. PWM, 4-polig",
                "Merkmale": "z.B. RGB-Lüfter, Gummischläuche"
            },
            "Verschiedenes": {
                "Montagekit": "Mitgeliefert",
                "Leistungsmerkmale": "z.B. Corsair iCUE",
                "Zubehör im Lieferumfang": "Liste"
            },
            "Herstellergarantie": {
                "Service und Support": "Dauer"
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
        
    elif "wlan" in cat_lower or "wifi" in cat_lower or "bluetooth" in cat_lower or "netzwerk" in cat_lower or "network" in cat_lower or "adapter" in cat_lower or "nic" in cat_lower or "lan" in cat_lower or "ethernet" in cat_lower:
        return base_prompt + """
        Kategorie: Netzwerkadapter (WLAN / LAN / Bluetooth)
        ERSTELLE EIN HIERARCHISCHES JSON (IT-Scope Datenblatt Style).

        CRITICAL INSTRUCTIONS:
        1. TYP: USB-Stick (extern) oder PCI-Express Karte (intern)?
        2. LAN-SPECS: Wake-on-LAN? Jumbo Frames? Vollduplex? Speed (10/100/1000)?
        3. WLAN-SPECS: WiFi 6/6E? Frequenz (2.4/5GHz)? Antennen?
        4. SCHNITTSTELLE: PCIe x1, USB 3.0, RJ-45?

        Benötigte JSON-Struktur:
        {
            "Allgemein": {
                "Gerätetyp": "z.B. Netzwerkadapter",
                "Formfaktor": "z.B. Extern (USB) oder Plug-in-Karte",
                "Schnittstellentyp": "z.B. PCI Express / USB 2.0",
                "Farbe": "z.B. Grün / Schwarz"
            },
            "Anschlüsse und Schnittstellen": {
                "Hostschnittstelle": "z.B. PCI Express",
                "Schnittstelle": "z.B. Ethernet / WLAN",
                "Anzahl Ethernet-LAN-Anschlüsse (RJ-45)": "Anzahl",
                "Übertragungstechnik": "z.B. Verkabelt / Kabellos"
            },
            "Netzwerk": {
                "Anschlusstechnik": "Kabellos / Verkabelt",
                "Maximale Datenübertragungsrate": "z.B. 1000 Mbit/s",
                "Ethernet LAN Datentransferraten": "z.B. 10,100,1000 Mbit/s",
                "Verkabelungstechnologie": "z.B. 10/100/1000BaseT(X)",
                "Netzstandard": "Liste (z.B. IEEE 802.3, IEEE 802.3u)",
                "Data Link Protocol": "z.B. Ethernet, Fast Ethernet, Gigabit Ethernet, Bluetooth 5.2, Wi-Fi 6",
                "Vollduplex": "Ja / Nein",
                "Jumbo Frames Unterstützung": "Ja / Nein",
                "Wake-on-LAN bereit": "Ja / Nein",
                "Frequenzband": "z.B. 2.4 GHz, 5 GHz (nur WLAN)",
                "Leistungsmerkmale": "z.B. QoS, Energy Efficient Ethernet",
                "Statusanzeiger": "z.B. Link/Aktivität"
            },
            "Antenne": {
                "Antenne": "z.B. Extern abnehmbar",
                "Antennenanzahl": "z.B. 2"
            },
            "Systemanforderung": {
                "Unterstützt Windows-Betriebssysteme": "Liste",
                "Unterstützte Linux-Betriebssysteme": "Ja / Nein"
            },
            "Betriebsbedingungen": {
                "Temperaturbereich in Betrieb": "z.B. 0 - 40 °C",
                "Temperaturbereich bei Lagerung": "z.B. -40 - 70 °C"
            },
             "Herstellergarantie": {
                "Service und Support": "Dauer"
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
        
    elif "tastatur" in cat_lower or "keyboard" in cat_lower or "maus" in cat_lower or "mouse" in cat_lower or "eingabegerät" in cat_lower:
        return base_prompt + """
        Kategorie: Eingabegerät (Tastatur / Maus / Set)
        ERSTELLE EIN HIERARCHISCHES JSON (IT-Scope Datenblatt Style).

        CRITICAL INSTRUCTIONS:
        1. TYP-CHECK: Ist es NUR eine Maus? NUR eine Tastatur? Oder ein SET?
        2. TASTATUR-DATEN: Fülle "Eingabegerät" (Switches, Layout, N-Key Rollover).
        3. MAUS-DATEN: Fülle "Zeigegerät" (DPI, Sensor, Tastenanzahl).
        4. VERBINDUNG: "Verkabelt" (USB) oder "Kabellos" (2.4 GHz/Bluetooth). Batterien?

        Benötigte JSON-Struktur:
        {
            "Allgemein": {
                "Gerätetyp": "z.B. Maus / Tastatur / Tastatur-und-Maus-Set",
                "Schnittstelle": "z.B. USB, 2.4 GHz, Bluetooth",
                "Kabelloser Empfänger": "z.B. Nano USB-Empfänger",
                "Hintergrundbeleuchtung": "z.B. RGB / Nein",
                "Farbe": "z.B. Schwarz"
            },
            "Eingabegerät": {
                "Typ": "Tastatur",
                "Tastaturtechnologie": "z.B. Mechanisch, Schere, Membran",
                "Key Switch Typ": "z.B. Cherry MX Red, Razer Green",
                "Lokalisierung und Layout": "z.B. QWERTZ / Deutsch",
                "Formfaktor": "z.B. Full-Size (100%), Tenkeyless (TKL)",
                "Tastenanzahl": "z.B. 105",
                "Anti-Ghosting": "Ja / Nein",
                "Handgelenkauflage": "Ja / Nein",
                "Abmessungen (BxTxH)": "cm",
                "Gewicht": "g"
            },
            "Zeigegerät": {
                "Typ": "Maus",
                "Movement Detection Technologie": "z.B. Optisch / Laser",
                "Bewegungsauflösung": "z.B. 26000 dpi",
                "Anzahl Tasten": "z.B. 11",
                "Leistung": "z.B. 50 G Beschleunigung, 650 IPS",
                "Ausrichtung": "z.B. Rechts, Beidhändig",
                "Abmessungen (BxTxH)": "cm",
                "Gewicht": "g"
            },
            "Verschiedenes": {
                "Zubehör im Lieferumfang": "z.B. Batterien, Handballenauflage",
                "Kabellänge": "m",
                "Software & Systemanforderungen": "z.B. Razer Synapse, Windows 10/11"
            },
             "Herstellergarantie": {
                "Service und Support": "Dauer (z.B. 2 Jahre)"
            }
        }
        """  
        
    elif "headset" in cat_lower or "kopfhörer" in cat_lower or "audio" in cat_lower or "lautsprecher" in cat_lower or "speaker" in cat_lower or "soundbar" in cat_lower:
        return base_prompt + """
        Kategorie: Audio (Headset / Lautsprecher)
        ERSTELLE EIN HIERARCHISCHES JSON (IT-Scope Datenblatt Style).

        CRITICAL INSTRUCTIONS:
        1. TYP: "Headset" oder "Lautsprecher" (Portable/Stereo)?
        2. HEADSET-DATEN: Mikrofon (Typ, Frequenz), Treiber (50mm), Akku (Laufzeit).
        3. LAUTSPRECHER-DATEN: RMS-Leistung (Watt), Kanäle (2.0), Verstärker (Eingebaut?).
        4. VERBINDUNG: USB, Klinke (3.5mm), Bluetooth?

        Benötigte JSON-Struktur:
        {
            "Allgemein": {
                "Produkttyp": "z.B. Headset - kabellos - USB / Tragbarer Stereo-Lautsprecher",
                "Kopfhörer-Formfaktor": "z.B. Ohrumschließend (nur Headset)",
                "Empfohlene Verwendung": "z.B. Spielkonsole, Computer, PC",
                "Farbe": "z.B. Schwarz / Stahlgrau",
                "Gewicht": "g",
                "Breite": "cm", "Tiefe": "cm", "Höhe": "cm",
                "Lokalisierung": "z.B. Europa"
            },
            "Audioausgang": {
                "Anschlusstechnik": "z.B. Kabellos / Verkabelt",
                "Soundmodus": "z.B. Stereo / 7.1 Channel Surround",
                "Frequenzgang": "z.B. 20 - 20000 Hz",
                "Impedanz": "z.B. 32 Ohm",
                "Empfindlichkeit": "dB",
                "Membran": "z.B. 50 mm",
                "Eingebaute Decoder": "z.B. Dolby Atmos",
                "Magnetmaterial": "z.B. Neodym"
            },
            "Lautsprecher": {
                "Lautsprechertyp": "z.B. 1-Weg / 2-Weg",
                "Audio Kanäle": "z.B. 2.0 Kanäle",
                "Anzahl des Antriebs": "Anzahl"
            },
            "Audio": {
                "RMS-Leistung": "z.B. 1.2 W (nur Lautsprecher)"
            },
            "Mikrofon": {
                "Typ": "z.B. Mikrofonbaum",
                "Formfaktor": "z.B. Headset Mikrofon",
                "Betriebsart des Mikrofons": "z.B. Ungerichtet / Omnidirektional",
                "Frequenzgang": "Hz",
                "Empfindlichkeit": "dB",
                "Impedanz": "Ohm"
            },
            "Verbindungen": {
                "Anschlusstyp": "z.B. USB / 3.5 mm",
                "Übertragungstechnik": "z.B. Verkabelt"
            },
            "Stromversorgung": {
                "Batterie": "z.B. Headset-Akku wiederaufladbar",
                "Betriebszeit (bis zu)": "z.B. 130 Stunden",
                "Laufzeitdetails": "Details zur Laufzeit",
                "Energiequelle": "z.B. USB"
            },
            "Verschiedenes": {
                "Zubehör im Lieferumfang": "z.B. USB-Drahtlosempfänger",
                "Kabeldetails": "z.B. USB-C Ladekabel - 1.8 m",
                "Zusätzliche Funktionen": "z.B. RGB-Beleuchtung"
            },
             "Herstellergarantie": {
                "Service und Support": "Dauer"
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
        
    elif "mauspad" in cat_lower or "mousepad" in cat_lower or "deskmat" in cat_lower or "schreibtischunterlage" in cat_lower:
        return base_prompt + """
        Kategorie: Mauspad / Schreibtischunterlage
        ERSTELLE EIN HIERARCHISCHES JSON (IT-Scope Datenblatt Style).

        CRITICAL INSTRUCTIONS:
        1. GRÖSSE: Maße in mm (Breite x Tiefe x Höhe). Größenklasse (XL, Extended?).
        2. MATERIAL: Stoff (Soft) oder Hartplastik (Hard)?
        3. FEATURES: RGB, Vernähte Ränder, Anti-Rutsch?

        Benötigte JSON-Struktur:
        {
            "Allgemein": {
                "Gerätetyp": "Mauspad",
                "Produktmaterial": "z.B. Stoff, Gummi, Kunststoff",
                "Farbe": "z.B. Schwarz",
                "Breite": "cm", "Tiefe": "cm", "Höhe": "cm"
            },
            "Verschiedenes": {
                "Besonderheiten": "z.B. Rutschfeste Unterseite, genähte Ränder, RGB-Beleuchtung",
                "Größenklasse": "z.B. XXL / Extended"
            },
            "Herstellergarantie": {
                "Service und Support": "Dauer"
            }
        }
        """  
        
    elif "service" in cat_lower or "garantie" in cat_lower or "warranty" in cat_lower or "dienstleistung" in cat_lower or "care pack" in cat_lower or "bearbeitung" in cat_lower:
        return base_prompt + """
        Kategorie: Service / Dienstleistung
        ERSTELLE EIN HIERARCHISCHES JSON (IT-Scope Datenblatt Style).

        CRITICAL INSTRUCTIONS:
        1. ART: Garantieerweiterung, Versicherung, Montage?
        2. DAUER: Laufzeit (z.B. 3 Jahre).
        3. MODUS: Vor-Ort, Bring-In, Pick-Up?

        Benötigte JSON-Struktur:
        {
            "Allgemein": {
                "Produkttyp": "z.B. Serviceerweiterung / Garantieverlängerung",
                "Dienstleistungstyp": "z.B. Extended Service Agreement",
                "Lokalisierung": "z.B. Europa / Deutschland"
            },
            "Details": {
                "Service inbegriffen": "z.B. Arbeitszeit und Ersatzteile",
                "Volle Vertragslaufzeit": "z.B. 3 Jahre",
                "Reaktionszeit": "z.B. Am nächsten Arbeitstag",
                "Serviceverfügbarkeit": "z.B. 9 Stunden am Tag / 5 Tage die Woche"
            },
             "Herstellergarantie": {
                "Service und Support": "Details"
            }
        }
        """
        
    elif ("usb" in cat_lower and ("stick" in cat_lower or "flash" in cat_lower or "drive" in cat_lower or "speicher" in cat_lower)) and "wlan" not in cat_lower and "wifi" not in cat_lower and "bluetooth" not in cat_lower:
        return base_prompt + """
        Kategorie: USB-Stick (Flash Drive)
        ERSTELLE EIN HIERARCHISCHES JSON (IT-Scope Datenblatt Style).

        CRITICAL INSTRUCTIONS:
        1. STRUKTUR: Nutze exakt die Blöcke "Leistungen", "Design", "Gewicht und Abmessungen".
        2. DATEN: Kapazität (GB), USB-Version (z.B. 3.2 Gen 1), Schnittstelle (Typ-A/C).
        3. DESIGN: Formfaktor (z.B. Dia/Kappe), Schlüsselanhänger (Ja/Nein).

        Benötigte JSON-Struktur:
        {
            "Leistungen": {
                "Kapazität": "z.B. 128 GB",
                "Geräteschnittstelle": "z.B. USB Typ-A",
                "USB-Version": "z.B. 3.2 Gen 1 (3.1 Gen 1)",
                "Lesegeschwindigkeit": "MB/s (falls verfügbar)",
                "Kompatible Betriebssysteme": "Liste (z.B. Windows 10, Linux, MacOS)"
            },
            "Design": {
                "Formfaktor": "z.B. Kappe / Schieber / Dia",
                "Produktfarbe": "z.B. Black, Red",
                "Schlüsselanhänger": "Ja / Nein"
            },
            "Lieferumfang": {
                "Menge pro Packung": "z.B. 1 Stück(e)"
            },
            "Gewicht und Abmessungen": {
                "Breite": "mm", "Tiefe": "mm", "Höhe": "mm", "Gewicht": "g"
            },
            "Betriebsbedingungen": {
                "Betriebstemperatur": "z.B. 0 - 60 °C",
                "Temperaturbereich bei Lagerung": "z.B. -20 - 85 °C"
            },
             "Herstellergarantie": {
                "Service und Support": "Dauer"
            }
        }
        """                                       
             
    #Fallback, neu Kategorien werden genau hier drüber eingefügt
    else:
        return base_prompt + """
        Identifiziere die Kategorie selbst.
        Erstelle ein sinnvolles, hierarchisches JSON.
        """