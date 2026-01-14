import json
import os
import re

class MarvinMapper:
    def __init__(self, output_folder="output_JSON_Marvin"):
        self.output_folder = output_folder
        if not os.path.exists(output_folder):
            os.makedirs(output_folder)

    def extract_number(self, text):
        """Holt die erste Ganzzahl (Integer) aus einem String"""
        if not text or text == "N/A": return 0
        # Entfernt Tausendertrennzeichen für sauberes Parsing
        clean_text = str(text).replace('.', '').replace(',', '.')
        match = re.search(r'(\d+)', clean_text)
        return int(match.group(1)) if match else 0

    def extract_float(self, text):
        """Holt eine Kommazahl (Float) aus einem String (z.B. '3.2 GHz' -> 3.2)"""
        if not text or text == "N/A": return 0.0
        # Ersetze Komma durch Punkt für Python
        clean_text = str(text).replace(',', '.')
        # Suche nach Zahlen mit optionalem Punkt (z.B. 3.2 oder 5)
        match = re.search(r'(\d+\.\d+|\d+)', clean_text)
        return float(match.group(1)) if match else 0.0

    def clean_brand_name(self, full_name, remove_list):
        """Bereinigt den Namen"""
        clean = full_name
        for item in remove_list:
            if item:
                clean = re.sub(fr'\b{re.escape(str(item))}\b', '', clean, flags=re.IGNORECASE)
        
        patterns = [r'- Kit -', r'\bKit\b', r'^\W+', r'\W+$', r'\s+GB\s+', r'\s+MHz\s+', r'Prozessor']
        for p in patterns:
            clean = re.sub(p, ' ', clean, flags=re.IGNORECASE)
        return " ".join(clean.split())
    
    def _extract_value_with_unit(self, text, unit_regex):
        """
        Sucht gezielt nach einer Zahl, die VOR einer bestimmten Einheit steht.
        Verhindert Fehler wie '2 x 120mm', wo '2' statt '120' gefunden wurde.
        
        Args:
            text (str): Der zu durchsuchende Text.
            unit_regex (str): Regex für die Einheit (z.B. r'mm|cm' oder r'W|Watt').
        """
        if not text: return 0.0
        
        # Muster: Zahl (mit optionaler Komma/Punkt) + optional Leerzeichen + Einheit
        # Beispiel: "150 Watt", "16.5mm", "120 mm"
        pattern = fr'(\d+([.,]\d+)?)\s*({unit_regex})'
        match = re.search(pattern, str(text), re.IGNORECASE)
        
        if match:
            val_str = match.group(1).replace(',', '.')
            return float(val_str)
        return 0.0

    # ==========================================
    # 🐏 RAM MAPPER 
    # ==========================================
    def map_ram(self, data, html_content=""):
        allgemein = data.get("Allgemein", {})
        speicher = data.get("Arbeitsspeicher", {})
        p_name = data.get("Produktname", "")

        kap = allgemein.get("Kapazität", "0")
        takt = speicher.get("Geschwindigkeit", "0")
        lat = speicher.get("Latenzzeiten", "0")
        typ = speicher.get("Technologie", "")

        mem_size = self.extract_number(kap)
        clock = self.extract_number(takt)
        cl = self.extract_number(lat)
        
        is_ddr5 = "DDR5" in typ.upper()
        mem_type = "DDR5" if is_ddr5 else "DDR4"
        
        slots = 1
        match = re.search(r'(\d+)\s*x', kap)
        if match: slots = int(match.group(1))

        brand_clean = self.clean_brand_name(p_name, [str(mem_size)+"GB", mem_type, "CL"+str(cl)])
        short_name = f"{mem_size}GB {mem_type} {clock}MHz CL{cl} {brand_clean}"

        return {
            "kWarengruppe": 2,
            "Attribute": {
                "memSize": mem_size,
                "memSlots": slots,
                "casLatency": cl,
                "memType": mem_type,
                "ddr4ClockSpeed": clock if not is_ddr5 else 0,
                "ddr5ClockSpeed": clock if is_ddr5 else 0,
                "shortNameLang": short_name,
                "board_ram_slots": slots
            }
        }

    # ==========================================
    # 🧠 CPU MAPPER 
    # ==========================================
    def map_cpu(self, data, html_content=""):
        """Mapping für Warengruppe 7 (AMD) & 8 (Intel) - Final V2"""
        allg = data.get("Allgemein", {})
        cpu = data.get("Prozessor", {})
        mem = data.get("Speicher-Controller", {})
        
        p_name = data.get("Produktname", data.get("_Produktname", ""))
        
        # 1. Hersteller Bestimmen
        is_intel = "INTEL" in p_name.upper() or "CORE" in allg.get("Serie", "").upper()
        k_warengruppe = 8 if is_intel else 7
        
        # 2. Werte extrahieren
        sockel_raw = cpu.get("Sockel", "")
        # Sockel-Bereinigung für JTL Werteliste
        sockel_clean = sockel_raw
        if "1700" in sockel_raw: sockel_clean = "LGA1700"
        elif "1851" in sockel_raw: sockel_clean = "LGA1851"
        elif "1200" in sockel_raw: sockel_clean = "LGA1200"
        elif "AM5" in sockel_raw.upper(): sockel_clean = "AM5"
        elif "AM4" in sockel_raw.upper(): sockel_clean = "AM4"
        
        codename = allg.get("Codename", "")
        
        cores_total = self.extract_number(cpu.get("Gesamtkerne", "0"))
        threads = self.extract_number(cpu.get("Gesamtthreads", "0"))
        
        p_cores = self.extract_number(cpu.get("P-Cores (Anzahl)", "0"))
        e_cores = self.extract_number(cpu.get("E-Cores (Anzahl)", "0"))
        if p_cores == 0: p_cores = cores_total # Fallback für AMD

        # Floats benutzen (3.2 statt 3200)
        clock_base = self.extract_float(cpu.get("Taktfrequenz Basis", "0"))
        clock_turbo = self.extract_float(cpu.get("Taktfrequenz Turbo", "0"))
        
        clock_base_eff = self.extract_float(cpu.get("Taktfrequenz E-Core Basis", "0"))
        clock_turbo_eff = self.extract_float(cpu.get("Taktfrequenz E-Core Turbo", "0"))

        ddr5_speed = self.extract_number(mem.get("Max. Taktfrequenz DDR5", "0"))
        ddr4_speed = self.extract_number(mem.get("Max. Taktfrequenz DDR4", "0"))
        max_ram_gb = self.extract_number(mem.get("Max. Speicherkapazität", "0"))
        
        tdp = self.extract_number(cpu.get("TDP", "0"))
        tdp_max = self.extract_number(cpu.get("TDP (Max/Turbo)", "0"))
        if tdp_max == 0: tdp_max = tdp

        # Chipsatz Fallback (WICHTIG für Konfigurator!)
        chipsatz_komp = cpu.get("Chipsatz-Kompatibilität", "N/A")
        if chipsatz_komp == "N/A" or not chipsatz_komp:
            # Wenn leer, nimm den Sockel als "Chipsatz-Gruppe" an
            chipsatz_komp = sockel_clean

        # Shortname Generierung
        modell = allg.get("Modell", "").replace("Prozessor", "").strip()
        serie = allg.get("Serie", "")
        short_name = f"{serie} {modell} {cores_total}-Core"
        if is_intel and e_cores > 0:
            short_name += f" ({p_cores}P+{e_cores}E)"
        
        # 3. Das finale JSON bauen
        attributes = {
            "shortNameLang": short_name,
            "codename": codename,
            "socket": sockel_clean,
            "coreCount": p_cores,
            "threads": threads,
            "clockSpeed": clock_base,   
            "clockTurbo": clock_turbo,  
            "tdp": tdp,
            "tdpTurbo": tdp_max,
            "tdp_max": tdp_max,
            "ddr5ClockSpeed": ddr5_speed,
            "ddr4ClockSpeed": ddr4_speed,
            "memSizeMax": max_ram_gb,
            
            # Abhängigkeiten
            "mainboard_cpu_chipsatz": chipsatz_komp,
            "konfiggruppen_typ": "Prozessor"
        }

        # Nur für Intel (WG 8) die E-Core Felder
        if is_intel:
            attributes.update({
                "coreCountEff": e_cores,
                "clockSpeedEff": clock_base_eff,
                "clockTurboEff": clock_turbo_eff
            })

        return {
            "kWarengruppe": k_warengruppe,
            "Attribute": attributes
        }
        
    def map_gpu(self, data, html_content=""):
        """Mapping für Warengruppe 4: Grafikkarten - Final V2"""
        allg = data.get("Allgemein", {})
        mem = data.get("Arbeitsspeicher", {})
        sys = data.get("Systemanforderungen", {})
        dims = data.get("Abmessungen und Gewicht", {})
        p_name = data.get("Produktname", data.get("_Produktname", ""))

        # --- Werte extrahieren ---
        
        # Chipsatz & Hersteller (Werteliste)
        hersteller_raw = allg.get("Chipsatz-Hersteller", "")
        # Mapping auf JTL Liste (AMD|Intel|Nvidia)
        chipset_man = "Nvidia" if "NVIDIA" in hersteller_raw.upper() else ("AMD" if "AMD" in hersteller_raw.upper() else "Intel")
        
        chip = allg.get("Grafikprozessor", "")
        
        # Speicher
        vram_gb = self.extract_number(mem.get("Grösse", "0"))
        mem_tech_raw = mem.get("Technologie", "")
        # Mapping auf Otto Liste (-1|GDDR3|GDDR4|GDDR5|GDDR6|GDDR6X|GDDR7|shared-memory)
        mem_tech = "-1"
        if "GDDR7" in mem_tech_raw.upper(): mem_tech = "GDDR7"
        elif "GDDR6X" in mem_tech_raw.upper(): mem_tech = "GDDR6X"
        elif "GDDR6" in mem_tech_raw.upper(): mem_tech = "GDDR6"
        elif "GDDR5" in mem_tech_raw.upper(): mem_tech = "GDDR5"
        
        # Strom / Watt (Erweiterte Suche!)
        psu_req = self.extract_number(sys.get("Erforderliche Leistungsversorgung", "0")) # Empfohlenes Netzteil
        
        # Versuch 1: TDP Feld
        tdp = self.extract_number(sys.get("Stromverbrauch (TDP)", "0"))
        # Versuch 2: Leistungsaufnahme
        if tdp == 0:
             tdp = self.extract_number(sys.get("Leistungsaufnahme", "0"))
        # Versuch 3: TGP (Total Graphics Power)
        if tdp == 0:
             tdp = self.extract_number(sys.get("TGP", "0"))
        
        # Abmessungen (JTL will mm)
        length = self.extract_number(dims.get("Tiefe", "0"))
        width = self.extract_number(dims.get("Breite", "0"))
        height = self.extract_number(dims.get("Höhe", "0"))
        
        # Safety Check: Wenn Länge < 50 (z.B. 30 cm statt 300 mm), mal 10 nehmen
        if length < 50 and length > 0: length *= 10
        if width < 50 and width > 0: width *= 10
        if height < 50 and height > 0: height *= 10

        # Stromstecker (String)
        connectors = sys.get("Zusätzliche Anforderungen", "")

        # DX Version
        dx_val = "12" # Standard heute
        if "12" in allg.get("API-Unterstützung", ""): dx_val = "12 Ultimate"

        # Shortname Generierung
        brand_clean = self.clean_brand_name(p_name, [chip, str(vram_gb)+"GB", "NVIDIA", "AMD", "GeForce", "Radeon"])
        short_name = f"{vram_gb}GB {chipset_man} {chip} {brand_clean}"

        return {
            "kWarengruppe": 4,
            "Attribute": {
                "shortNameLang": short_name,
                "gpuChipsetManufacturer": chipset_man,
                "ottoMemType": mem_tech,
                "gpuTyp": "dediziert",
                "gpuVram": vram_gb,
                "length": length,
                "width": width,
                "height": height,
                "watt": tdp,
                "netzteil_grafik_watt": psu_req,
                "netzteil_grafik_8_pin_gpu": connectors,
                "directx": dx_val,
                "konfiggruppen_typ": "Grafikkarte"
            }
        }  

    def map_mainboard(self, data, html_content=""):
        """Mapping für Warengruppe 5: Mainboards (MSI/Pumpen/RGB Fix)"""
        allg = data.get("Allgemein", {})
        ram = data.get("Unterstützter RAM", {})
        conn = data.get("Erweiterung / Konnektivität", {})
        audio = data.get("Audio", {})
        lan = data.get("LAN", {})
        specials = data.get("Besonderheiten", {})
        p_name = data.get("Produktname", data.get("_Produktname", ""))

        # --- Erweiterte Zähl-Funktion ---
        def count_in_string(text, keywords):
            if not text or text == "N/A": return 0
            count = 0
            # Splitte am Trenner '¦', Komma, Zeilenumbruch oder " + "
            parts = re.split(r'[¦,\n\+]| plus ', str(text), flags=re.IGNORECASE)
            for part in parts:
                part = part.strip()
                if any(k.lower() in part.lower() for k in keywords):
                    # Versuche Zahl am Anfang zu finden ("2 x USB", "4x SATA")
                    match = re.search(r'^(\d+)\s*[xX]', part)
                    if match:
                        count += int(match.group(1))
                    else:
                        count += 1 
            return count

        # 1. Basis-Daten
        sockel_raw = allg.get("Prozessorsockel", "")
        sockel = sockel_raw
        if "AM5" in sockel_raw.upper(): sockel = "AM5"
        elif "AM4" in sockel_raw.upper(): sockel = "AM4"
        elif "1700" in sockel_raw: sockel = "LGA1700"
        elif "1851" in sockel_raw: sockel = "LGA1851"
        
        chipsatz = allg.get("Chipsatz", "").replace("AMD", "").replace("Intel", "").strip()
        
        formfaktor_raw = allg.get("Produkttyp", "")
        formfaktor = "ATX"
        if "micro" in formfaktor_raw.lower() or "mATX" in formfaktor_raw: formfaktor = "mATX"
        elif "mini-itx" in formfaktor_raw.lower() or "m-itx" in formfaktor_raw.lower(): formfaktor = "ITX"
        elif "e-atx" in formfaktor_raw.lower(): formfaktor = "E-ATX"

        # 2. RAM
        mem_tech = ram.get("Technologie", "DDR4")
        if "DDR5" in mem_tech.upper(): mem_tech = "DDR5"
        elif "DDR4" in mem_tech.upper(): mem_tech = "DDR4"
        
        mem_slots = self.extract_number(ram.get("Anzahl Steckplätze", "0"))
        if mem_slots == 0:
            if formfaktor == "ITX": mem_slots = 2
            else: mem_slots = 4
        
        mem_max = self.extract_number(ram.get("Max. Größe", "0"))
        
        bustakt_str = ram.get("Bustakt", "0")
        all_speeds = re.findall(r'(\d{4})', bustakt_str)
        max_speed = 0
        if all_speeds: max_speed = max([int(s) for s in all_speeds])
            
        ddr5_clock = max_speed if mem_tech == "DDR5" else 0
        ddr4_clock = max_speed if mem_tech == "DDR4" else 0

        # 3. Anschlüsse (Erweiterte Keywords)
        ports_back = conn.get("Schnittstellen (Rückseite)", "")
        ports_internal = conn.get("Schnittstellen (Intern)", "")
        storage = conn.get("Speicherschnittstellen", "")
        slots_str = conn.get("Erweiterungssteckplätze", "")
        
        # USB / Video / LAN
        usb_back_count = count_in_string(ports_back, ["USB"])
        hdmi_count = count_in_string(ports_back, ["HDMI"])
        dp_count = count_in_string(ports_back, ["DisplayPort"])
        
        lan_count = count_in_string(ports_back, ["LAN", "RJ-45", "Ethernet"])
        has_lan_chip = "LAN" in lan.get("Netzwerkcontroller", "") or "GbE" in lan.get("Netzwerkcontroller", "")
        if lan_count == 0 and has_lan_chip: lan_count = 1

        audio_jacks = count_in_string(ports_back, ["Audio", "Line-Out", "Microphone", "Jack"])
        if audio_jacks == 0 and "Audio" in audio.get("Audio Codec", ""): audio_jacks = 3
        
        # Storage
        sata_count = count_in_string(storage, ["SATA"])
        if sata_count == 0 and formfaktor != "ITX": sata_count = 4

        m2_count = count_in_string(storage, ["M.2"])
        pcie_count = count_in_string(slots_str, ["PCI Express", "PCIe"])
        
        # --- RGB & PUMP FIX (Hier war der Fehler!) ---
        
        # 4-Pin RGB (12V) - MSI nennt es oft JRGB
        kw_rgb_4pin = ["RGB LED", "JRGB", "RGB_HEADER", "RGB 12V", "LED_C"]
        rgb_header = count_in_string(ports_internal, kw_rgb_4pin)
        
        # 3-Pin ARGB (5V) - MSI nennt es JARGB, JRAINBOW
        kw_argb_3pin = ["ARGB", "Addressable", "Gen 2", "JRAINBOW", "JARGB", "ADD_GEN", "A_RGB", "AD_RGB"]
        argb_header = count_in_string(ports_internal, kw_argb_3pin)
        
        # Pumpe / AIO - MSI nennt es PUMP_SYS
        kw_pump = ["Pump", "AIO", "Water", "W_PUMP", "WP", "SYS_FAN_PUMP", "PUMP_SYS"]
        aio_pump = count_in_string(ports_internal, kw_pump)
        
        # Wakü-Anschluss (Oft identisch mit AIO Pump oder spezieller Flow-Header)
        wakue_anschluss = 1 if aio_pump > 0 or count_in_string(ports_internal, ["Flow", "Durchfluss"]) > 0 else 0

        has_onboard_rgb = 0 
        feature_text = str(specials) + str(allg)
        if "Onboard LED" in feature_text or "Beleuchtungszone" in feature_text:
            has_onboard_rgb = 1
            
        # Features
        has_wlan = 1 if "Wi-Fi" in lan.get("Netzwerkschnittstellen", "") or "WLAN" in lan.get("Netzwerkschnittstellen", "") else 0
        has_bt = 1 if "Bluetooth" in lan.get("Netzwerkschnittstellen", "") else 0
        
        # Dependencies
        tower_form = 3
        if formfaktor == "mATX": tower_form = 2
        elif formfaktor == "ITX": tower_form = 1
        elif formfaktor == "E-ATX": tower_form = 3
        
        has_p8 = 1 

        brand_clean = self.clean_brand_name(p_name, [chipsatz, sockel, mem_tech, formfaktor])
        short_name = f"{chipsatz} {brand_clean} {sockel} {mem_tech} {formfaktor}"

        return {
            "kWarengruppe": 5,
            "Attribute": {
                "shortNameLang": short_name,
                "socket": sockel,
                "chipset": chipsatz,
                "formFactor": formfaktor,
                "memType": mem_tech,
                "memSlots": mem_slots,
                "memSizeMax": mem_max,
                "ddr5ClockSpeed": ddr5_clock,
                "ddr4ClockSpeed": ddr4_clock,
                "board_ram_slots": mem_slots,
                "board_ram_ddrtyp": mem_tech,
                
                "usb": ports_back,
                "hdmi": hdmi_count,
                "displayPort": dp_count,
                "dvi": count_in_string(ports_back, ["DVI"]),
                "vga": count_in_string(ports_back, ["VGA", "D-Sub"]),
                "ps2": count_in_string(ports_back, ["PS/2"]),
                "rj45": lan_count,
                "audioJacks": audio_jacks,
                "audioOpticalOut": count_in_string(ports_back, ["S/PDIF", "Optical"]),
                "wifiAntennaJacks": 2 if has_wlan else 0,
                
                "usbHeader": ports_internal,
                "sata": sata_count,
                "m2Slots": m2_count,
                "m2SlotsNvme": m2_count,
                "m2SlotsSata": 0,
                "board_m2slots": m2_count,
                "board_sataslots": sata_count,
                "pcie": slots_str,
                "board_pcieslots": pcie_count,
                
                "audioChipset": audio.get("Audio Codec", "N/A"),
                "audioChannels": "7.1" if "7.1" in audio.get("Typ", "") else "5.1",
                "ethernetController": lan.get("Netzwerkcontroller", "N/A"),
                "wlan": has_wlan,
                "bluetooth": has_bt,
                "board_wlan": has_wlan,
                
                # --- KORRIGIERTE RGB/PUMP WERTE ---
                "rgb": has_onboard_rgb,             # Integrierte Beleuchtung (oft 0)
                "argb": 1 if argb_header > 0 else 0, # ARGB Fähigkeit (Header vorhanden -> Ja)
                "rgb_anschluss_4pin_rgb": rgb_header,
                "rgb_anschluss_3pin_argb": argb_header,
                "aioPump": 1 if aio_pump > 0 else 0, # Ja/Nein Flag für Pumpe
                "board_wakue_anschluss": wakue_anschluss, # Ja/Nein Flag
                # ----------------------------------
                
                "tower_board_bauform": tower_form,
                "board_netzteil_p8": has_p8,
                "board_netzteil_p4": 0,
                "mainboard_cpu_chipsatz": chipsatz,
                "board_cpukuehler_sockel": sockel,
                "konfiggruppen_typ": "Mainboard"
            }
        }
        
    def map_psu(self, data, html_content=""):
        """Mapping für Warengruppe 6: Netzteile (Fix: Stecker zählen)"""
        allg = data.get("Allgemein", {})
        strom = data.get("Stromversorgungsgerät", {})
        vers = data.get("Verschiedenes", {})
        p_name = data.get("Produktname", "")

        # 1. Leistung & Lüfter
        watt = self.extract_number(strom.get("Leistungskapazität", "0"))
        fan_str = vers.get("Kühlsystem", "")
        fan_mm = self.extract_number(fan_str)
        if fan_mm > 0 and fan_mm < 20: fan_mm *= 10
        if fan_mm == 0: fan_mm = 120 

        # 2. 80 PLUS Zertifikat
        cert_raw = strom.get("80-PLUS-Zertifizierung", "").upper()
        cert_str = "Standard"
        cert_int = 0
        
        if "TITANIUM" in cert_raw: cert_str, cert_int = "TITANIUM", 5
        elif "PLATINUM" in cert_raw: cert_str, cert_int = "PLATINUM", 4
        elif "GOLD" in cert_raw: cert_str, cert_int = "GOLD", 3
        elif "SILVER" in cert_raw: cert_str, cert_int = "SILVER", 2
        elif "BRONZE" in cert_raw: cert_str, cert_int = "BRONZE", 1
        elif "80 PLUS" in cert_raw: cert_str, cert_int = "Standard", 0

        # 3. Anschlüsse (PCIe SUMMIEREN!)
        conns = strom.get("Angaben zu Ausgangsleistungsanschlüssen", "")
        
        has_p8 = 1 if "EPS" in conns or "CPU" in conns else 1
        has_p4 = 1 if "4-polig" in conns and "ATX12V" in conns else 0
        
        # PCIe Summier-Logik
        pcie_count = 0
        # Suche nach Mustern wie "4 x 8-poliger PCI" oder "1 x PCIe"
        # Wir splitten den String erst, um Verwirrung zu vermeiden
        conn_parts = re.split(r'[¦,\n]', conns)
        for part in conn_parts:
            if "PCI" in part or "GPU" in part or "Grafik" in part:
                match = re.search(r'(\d+)\s*x', part)
                if match:
                    pcie_count += int(match.group(1))
        
        # Fallback wenn Regex versagt, aber Wattzahl hoch ist
        if pcie_count == 0:
            if watt >= 1000: pcie_count = 6
            elif watt >= 850: pcie_count = 4
            elif watt >= 650: pcie_count = 2
            elif watt >= 450: pcie_count = 1
            
        pcie_str = f"{pcie_count}x 6+2-Pin" if pcie_count > 0 else "N/A"

        # 4. Shortname
        brand_clean = self.clean_brand_name(p_name, ["Netzteil", str(watt)+"W", "80 Plus", cert_str, "Watt"])
        short_name = f"{watt}W {brand_clean} {cert_str}"

        return {
            "kWarengruppe": 6,
            "Attribute": {
                "shortNameLang": short_name,
                "watt": watt,
                "fanDiameter": fan_mm,
                "80PlusExtra": cert_str,
                "netzteil_wirkungsgrad": cert_int,
                "board_netzteil_p8": has_p8,
                "board_netzteil_p4": has_p4,
                "netzteil_grafik_8_pin_gpu": pcie_str,
                "netzteil_grafik_watt": watt,
                "efficiency": self.extract_number(strom.get("Effizienz", "0")),
                "Seriennummer": 1,
                "upgradeArticle": 1,
                "konfiggruppen_typ": "Netzteil",
                "silent": 1 if "Silent" in p_name or "Quiet" in p_name else 0,
                "markup": 0,
                "Hardware": 0
            }
        }    
    
    def map_case(self, data, html_content=""):
        """Mapping für Warengruppe 3: Gehäuse"""
        allg = data.get("Allgemein", {})
        cool_in = data.get("Kühlsystem (Installiert)", {})
        cool_sup = data.get("Kühlsystem (Unterstützt)", {})
        sys_req = data.get("Systemanforderungen", {})
        dims = data.get("Abmessungen und Gewicht", {})
        conn = data.get("Erweiterung / Konnektivität", {})
        p_name = data.get("Produktname", data.get("_Produktname", ""))

        # 1. Maße & Limits
        width = self.extract_number(dims.get("Breite", "0"))
        height = self.extract_number(dims.get("Höhe", "0"))
        length = self.extract_number(dims.get("Tiefe", "0")) # Tiefe = Länge
        
        # Safety Check: cm -> mm (wenn < 100)
        if width < 100 and width > 0: width *= 10
        if height < 100 and height > 0: height *= 10
        if length < 100 and length > 0: length *= 10

        gpu_max = self.extract_number(sys_req.get("Max. Länge Grafikkarte", "0"))
        cpu_max = self.extract_number(sys_req.get("Max. Höhe CPU-Kühler", "0"))
        
        # 2. Formfaktor (ATX=3, mATX=2, ITX=1)
        mb_support = allg.get("Unterstützte Mainboards", "") + allg.get("Max. Mainboard-Größe", "")
        
        tower_form = 1 # ITX Default
        form_str = "ITX"
        
        if "E-ATX" in mb_support or "Extended ATX" in mb_support:
            tower_form = 3
            form_str = "ATX" # E-ATX mappen wir oft auf ATX oder lassen es als ATX laufen
        elif "ATX" in mb_support: # Normales ATX
            tower_form = 3
            form_str = "ATX"
        elif "Micro-ATX" in mb_support or "mATX" in mb_support:
            tower_form = 2
            form_str = "mATX"
            
        # 3. Lüfter zählen
        # Wir zählen installierte Lüfter im String "1 x 120mm..."
        def count_fans(text_dict):
            total = 0
            for val in text_dict.values():
                match = re.search(r'(\d+)\s*x', str(val))
                if match:
                    total += int(match.group(1))
            return total

        fans_inc = count_fans(cool_in)
        
        # Max Lüfter
        fans_max = self.extract_number(cool_sup.get("Lüfterhalterungen (Gesamt)", "0"))
        if fans_max == 0: fans_max = fans_inc + 2 # Fallback: Mindestens 2 mehr als drin sind

        # 4. AIO Support (Größter Radiator)
        rad_front = self.extract_number(cool_sup.get("Radiatorgröße (Vorne)", "0"))
        rad_top = self.extract_number(cool_sup.get("Radiatorgröße (Oben)", "0"))
        aio_max = max(rad_front, rad_top)
        
        # Auf Standardwerte mappen (120, 240, 280->280?, 360)
        # JTL Liste: 0|120|240|360
        aio_val = "0"
        if aio_max >= 360: aio_val = "360"
        elif aio_max >= 240: aio_val = "240"
        elif aio_max >= 120: aio_val = "120"

        # 5. Features
        has_rgb = 1 if "RGB" in str(cool_in) or "RGB" in allg.get("Besonderheiten", "") else 0
        is_silent = 1 if "Dämmung" in allg.get("Besonderheiten", "") or "Silent" in p_name else 0
        
        # Farbe
        color = allg.get("Farbe", "Schwarz") # Default Schwarz

        # Shortname
        brand_clean = self.clean_brand_name(p_name, ["Gehäuse", "Tower", "Midi", "Case", form_str])
        short_name = f"{form_str} {brand_clean} {color}"

        return {
            "kWarengruppe": 3,
            "Attribute": {
                "shortNameLang": short_name,
                "formFactor": form_str, # ATX|mATX|ITX
                "tower_board_bauform": tower_form, # 3|2|1
                
                "width": width,
                "height": height,
                "length": length,
                
                "tower_grafik_groesse": gpu_max, # Max GPU Länge
                "cpukuehler_bauhoehe": cpu_max,  # Max CPU Höhe
                
                "fansInc": fans_inc,
                "fansMax": fans_max,
                "aioSlots": aio_val, # 120|240|360
                "wakue_slots": 1 if aio_max > 0 else 0, # Generell Wakü möglich?
                
                "rgb": has_rgb,
                "silent": is_silent,
                "color": color,
                
                "tower_lw_slots": 0, # Laufwerksschächte (heute fast immer 0)
                "low_profile": 0,
                
                "konfiggruppen_typ": "Gehäuse",
                "upgradeArticle": 1,
                "Seriennummer": 1,
                "markup": 0,
                "Hardware": 0
            }
        }
        
    def map_storage(self, data, html_content=""):
        """Mapping für Warengruppe 13: Speicher (Fix: Speed Plausibilität)"""
        allg = data.get("Allgemein", {})
        perf = data.get("Leistung", {})
        p_name = data.get("Produktname", data.get("_Produktname", ""))

        # 1. Typ Bestimmung
        form = allg.get("Formfaktor", "")
        interf = allg.get("Schnittstelle", "")
        dev_type = allg.get("Gerätetyp", "")
        
        disk_type = "SSD"
        if "HDD" in dev_type or "Festplatte" in dev_type or "7200" in str(perf.get("Spindelgeschwindigkeit", "")):
            disk_type = "HDD"
        elif "M.2" in form:
            if "NVMe" in interf or "PCI" in interf: disk_type = "M.2 NVMe"
            else: disk_type = "M.2 SATA"
        elif "2.5" in form:
            disk_type = "SSD"

        # 2. Kapazität
        cap_raw = allg.get("Kapazität", "0")
        cap_gb = 0
        match_tb = re.search(r'(\d+)\s*TB', cap_raw, re.IGNORECASE)
        if match_tb: cap_gb = int(match_tb.group(1)) * 1000
        else:
            match_gb = re.search(r'(\d+)', cap_raw)
            if match_gb: cap_gb = int(match_gb.group(1))

        # 3. Geschwindigkeit (Mit Plausibilitäts-Check)
        def get_speed(val):
            if not val or val == "N/A": return 0
            val_str = str(val).upper()
            is_gb = "GB" in val_str
            num = self.extract_float(val_str)
            
            speed = int(num * 1000) if is_gb else int(num)
            
            # Plausibilitäts-Check: Unter 100 MB/s ist für SSDs meist ein Fehler (z.B. Schnittstellen-Speed gelesen)
            if speed < 100 and disk_type != "HDD":
                return 0 # Ungültig, lieber 0 als 6 MB/s
            return speed

        read_speed = get_speed(perf.get("Interner Datendurchsatz (Lesen)", "0"))
        write_speed = get_speed(perf.get("Interner Datendurchsatz (Schreiben)", "0"))
        
        # Fallback NVMe
        if read_speed < 500 and disk_type == "M.2 NVMe": read_speed = 3500

        # 4. Shortname & Dependencies
        is_m2 = "M.2" in disk_type
        
        remove_items = [disk_type, cap_raw, cap_raw.replace(" ", ""), "SSD", "HDD", "M.2", "NVMe", "Interne", "Solid State Drive", "Gen4"]
        brand_clean = self.clean_brand_name(p_name, remove_items)
        brand_clean = re.sub(r'\(\s*\)', '', brand_clean).strip()
        
        short_name = f"{cap_raw} {brand_clean} {disk_type}"

        return {
            "kWarengruppe": 13,
            "Attribute": {
                "shortNameLang": short_name,
                "diskType": disk_type,
                "diskSize": cap_gb,
                "readingSpeed": read_speed,
                "writingSpeed": write_speed,
                "board_m2slots": 1 if is_m2 else 0,
                "board_sataslots": 1 if not is_m2 else 0,
                "konfiggruppen_typ": "Festplatte" if disk_type == "HDD" else "SSD",
                "Seriennummer": 1,
                "upgradeArticle": 1,
                "markup": 0,
                "Hardware": 0
            }
        } 
        
    def map_monitor(self, data, html_content=""):
        """Mapping für Warengruppe 10: Monitore / TFTs (Optimiert)"""
        allg = data.get("Allgemein", {})
        disp = data.get("Display", {})
        conn = data.get("Schnittstellen", {})
        p_name = data.get("Produktname", data.get("_Produktname", ""))

        # 1. Zollgröße (screenInch)
        diag_str = disp.get("Diagonale", "")
        inch = 24.0 # Fallback
        match_inch = re.search(r'(\d{2,3}(\.\d)?)', diag_str)
        if match_inch:
            inch = float(match_inch.group(1))

        # 2. Auflösung (resolution)
        res_raw = disp.get("Auflösung", "")
        res_match = re.search(r'(\d{3,4})\s*[xX]\s*(\d{3,4})', res_raw)
        
        resolution = "1920x1080"
        if res_match:
            w = res_match.group(1)
            h = res_match.group(2)
            resolution = f"{w}x{h}"

        # 3. Anschlüsse
        ports_str = conn.get("Anschlüsse", "")
        
        def count_ports(keyword):
            count = 0
            parts = re.split(r'[¦,\n]', str(ports_str))
            for part in parts:
                if keyword.lower() in part.lower():
                    match = re.search(r'(\d+)\s*x', part)
                    if match: count += int(match.group(1))
                    else: count += 1
            return count

        hdmi = count_ports("HDMI")
        dp = count_ports("DisplayPort")
        dvi = count_ports("DVI")
        vga = count_ports("VGA") + count_ports("D-Sub")

        panel = disp.get("Panel-Typ", "").replace("Panel", "").strip()
        if len(panel) > 10: panel = "" # Schutz vor langen Sätzen
        
        # Unnötige Wörter entfernen
        remove_list = [
            "Monitor", "TFT", "Display", "Zoll", str(int(inch)), resolution, 
            "LED", "LCD", "Gaming", "Screen", "cm", "Backlight", "hintergrundbeleuchteter"
        ]
        
        # Versuche auch "68.6 cm" dynamisch zu entfernen
        match_cm = re.search(r'(\d+(\.\d)?)\s*cm', p_name)
        if match_cm: 
            remove_list.append(match_cm.group(0)) # Entfernt "68.6 cm"
            remove_list.append(match_cm.group(1)) # Entfernt "68.6" (die Zahl alleine)

        brand_clean = self.clean_brand_name(p_name, remove_list)
        
        # Bereinige hässliche Reste wie "- - " oder "()"
        brand_clean = re.sub(r'[-–]\s*[-–]', '', brand_clean) # Doppelte Striche
        brand_clean = re.sub(r'^\W+|\W+$', '', brand_clean)   # Sonderzeichen am Anfang/Ende
        brand_clean = re.sub(r'\(\s*\)', '', brand_clean)     # Leere Klammern
        
        # Hz Zahl
        hz_str = disp.get("Bildwiederholrate", "")
        hz = self.extract_number(hz_str)
        hz_info = f"{hz}Hz" if hz > 60 else ""
        
        # Bau den Namen: "27 Zoll ASUS ProArt PA279CRV IPS 3840x2160"
        short_name = f"{inch:.0f} Zoll {brand_clean} {panel} {resolution} {hz_info}".strip()
        short_name = " ".join(short_name.split())

        return {
            "kWarengruppe": 10,
            "Attribute": {
                "shortNameLang": short_name,
                "screenInch": f"{inch:.0f}",
                "resolution": resolution,
                "hdmi": hdmi,
                "displayPort": dp,
                "dvi": dvi,
                "vga": vga,
                "tft_kartonage_zoll": int(inch),
                
                "konfiggruppen_typ": "Monitor",
                "Seriennummer": 1,
                "upgradeArticle": 1,
                "markup": 0,
                "Hardware": 0
            }
        }   
    
    def map_fan(self, data, html_content=""):
        """Mapping für Warengruppe 11: Gehäuselüfter (mit Namens-Bereinigung)"""
        allg = data.get("Allgemein", {})
        tech = data.get("Technische Daten", {})
        feat = data.get("Anschlüsse & Features", {})
        p_name = data.get("Produktname", data.get("_Produktname", ""))

        # 1. Größe (Wichtigstes Merkmal)
        # Suche nach "120", "140", "80", "200" im Durchmesser
        size_str = tech.get("Lüfterdurchmesser", "")
        size = "120" # Fallback
        match_size = re.search(r'(\d{2,3})', size_str)
        if match_size:
            size = match_size.group(1)

        # 2. Features für den Namen
        # PWM Check
        is_pwm = "PWM" in feat.get("Stromanschluss", "").upper() or "PWM" in p_name.upper()
        
        # RGB Check
        rgb_str = feat.get("Beleuchtung", "").upper()
        is_argb = "ARGB" in rgb_str or "ADDRESSABLE" in rgb_str
        is_rgb = "RGB" in rgb_str and not is_argb
        
        # 3. Paketgröße (Single / Triple Pack)
        pack_qty = self.extract_number(allg.get("Paketmenge", "1"))
        pack_str = ""
        if pack_qty > 1:
            pack_str = f"{pack_qty}er-Pack"
        
        # 4. Shortname Bauen
        # Ziel: "120mm Neutral PWM" (statt "120mm 120x120 - Neutral PWM")
        
        # Attribute sammeln
        attrs = []
        if is_argb: attrs.append("ARGB")
        elif is_rgb: attrs.append("RGB")
        if is_pwm: attrs.append("PWM")
        
        color = allg.get("Farbe", "")
        # Schwarz ist Standard, muss oft nicht in den Titel, außer es steht explizit da
        if color and color.lower() not in ["schwarz", "n/a"]: 
            attrs.append(color)
            
        attr_string = " ".join(attrs)
        
        # --- NAME CLEANING ---
        
        # Schritt A: Maße wie "120x120" oder "140 x 140" entfernen
        p_name_clean = re.sub(r'\d+\s*[xX]\s*\d+', '', p_name)
        
        # Schritt B: Liste der zu entfernenden Wörter
        remove_list = [
            "Gehäuselüfter", "Fan", "Lüfter", "Cooling", "Case", 
            size + "mm", size + " mm", size, # Größe entfernen
            "PWM", "RGB", "ARGB", "LED", "Neutral", # Auch "Neutral" entfernen
            pack_str, "Pack", "Kit", "Triple", "Duo"
        ]
        
        brand_clean = self.clean_brand_name(p_name_clean, remove_list)
        
        # Schritt C: Reste aufräumen (doppelte Bindestriche etc.)
        brand_clean = re.sub(r'[-–]\s*[-–]', '', brand_clean)
        brand_clean = re.sub(r'^\W+|\W+$', '', brand_clean)
        
        short_name = f"{size}mm {brand_clean} {attr_string} {pack_str}".strip()
        short_name = " ".join(short_name.split()) # Doppelte Leerzeichen weg

        return {
            "kWarengruppe": 11,
            "Attribute": {
                "shortNameLang": short_name,
                "konfiggruppen_typ": "Gehäuselüfter",
                "Seriennummer": 1,
                "upgradeArticle": 1,
                "markup": 0,
                "Hardware": 0
            }
        }
        
    def map_cpu_cooler(self, data, html_content=""):
        """Mapping für Warengruppe 9: CPU-Kühler"""
        allg = data.get("Allgemein", {})
        komp = data.get("Kompatibilität", {})
        tech = data.get("Technische Daten", {})
        feat = data.get("Beleuchtung & Features", {})
        p_name = data.get("Produktname", data.get("_Produktname", ""))

        # 1. Typ Bestimmung (Luft vs AiO)
        is_aio = "aio" in str(allg).lower() or "wasser" in str(allg).lower() or "liquid" in p_name.lower()
        
        # 2. Bauhöhe (Nutze neuen Smart-Extraktor!)
        # JTL 'cpukuehler_bauhoehe' in mm
        height_mm = self._extract_value_with_unit(tech.get("Bauhöhe (nur Kühler)", ""), "mm")
        
        # Fallback für AiO: Wenn keine Block-Höhe da ist, nehmen wir oft 0 oder einen Standardwert,
        # da AiOs fast immer auf die CPU passen. Für Luftkühler ist der Wert kritisch.
        if is_aio and height_mm == 0:
            height_mm = 55 # Ca. Standard Pumpenhöhe, damit JTL nicht meckert
            
        # 3. Sockel & Typ-Logik
        sockets_str = str(komp.get("Sockel", ""))
        sockets_clean = sockets_str.replace("[", "").replace("]", "").replace("'", "")
        
        # Typ Berechnung: 1=AMD, 2=Intel, 3=Beide
        has_amd = "AM" in sockets_clean.upper() or "FM" in sockets_clean.upper()
        has_intel = "LGA" in sockets_clean.upper() or "1700" in sockets_clean or "1200" in sockets_clean
        
        cpu_kuehler_typ = 0
        if has_amd and has_intel: cpu_kuehler_typ = 3
        elif has_intel: cpu_kuehler_typ = 2
        elif has_amd: cpu_kuehler_typ = 1
        
        # 4. RGB Logik
        rgb_text = str(feat) + " " + p_name
        rgb_val = 1 if "RGB" in rgb_text else 0
        argb_val = 1 if "ARGB" in rgb_text or "Addressable" in rgb_text else 0
        
        # 5. TDP
        tdp = int(self._extract_value_with_unit(allg.get("TDP-Klasse", ""), "W|Watt"))
        
        # 6. Shortname Bauen
        # Ziel: "Be quiet! Dark Rock Pro 5 270W TDP" oder "Corsair H150i Elite 360mm AiO"
        rad_size = self._extract_value_with_unit(tech.get("Radiatorgröße", ""), "mm")
        
        suffix = ""
        if is_aio and rad_size > 0:
            suffix = f"{int(rad_size)}mm AiO"
        elif tdp > 0:
            suffix = f"{tdp}W TDP"
            
        remove_list = ["CPU-Kühler", "Cooler", "Wasserkühlung", "Liquid", "All-in-One", "TDP", "Watt"]
        brand_clean = self.clean_brand_name(p_name, remove_list)
        
        short_name = f"{brand_clean} {suffix}".strip()
        
        return {
            "kWarengruppe": 9,
            "Attribute": {
                "shortNameLang": short_name,
                "cpukuehler_bauhoehe": int(height_mm),
                "tdp": tdp,
                "rgb": rgb_val,
                "argb": argb_val,
                "rgb_anschluss_4pin_rgb": rgb_val,   # Annahme: Wenn RGB, dann meist Header da
                "rgb_anschluss_3pin_argb": argb_val, # Annahme: Wenn ARGB, dann Header da
                "cpukuehler_typ": cpu_kuehler_typ,
                "board_cpukuehler_sockel": sockets_clean[:255], # JTL Limit beachten
                "cpukuehler_breite": 1, # Standard: Passt fast immer (außer riesige Dinger)
                "silent": 1 if "silent" in str(data).lower() or "quiet" in p_name.lower() else 0,
                
                # Standards
                "konfiggruppen_typ": "CPU-Kühler",
                "Seriennummer": 1,
                "upgradeArticle": 1,
                "markup": 0,
                "Hardware": 0
            }
        }    
    
    # ==========================================
    # 🎛️ MAIN DISPATCHER (Fix: json_str defined)
    # ==========================================
    def create_json(self, source_file, data, html_content=None):
        filename = os.path.basename(source_file)
        
        # --- WICHTIG: Hier definieren wir die String-Variable für die Suche ---
        json_str = json.dumps(data).lower()
        
        # Wir holen uns die Schlüssel der obersten Ebene
        root_keys = [k.lower() for k in data.keys()]
        
        # Wir schauen auch kurz in "Allgemein" rein
        allgemein = data.get("Allgemein", {})
        allgemein_str = json.dumps(allgemein).lower()
        
        marvin_json = {}
        found_category = False
        cat_debug = ""

        # --- DETEKTION ANHAND DER STRUKTUR ---

        # 1. MAINBOARD CHECK
        if "unterstützter ram" in root_keys or ("chipsatz" in allgemein_str and "audio" in root_keys):
             try:
                marvin_json = self.map_mainboard(data, html_content)
                found_category = True
                cat_debug = "Mainboard"
             except Exception as e:
                print(f"   ❌ Fehler im Mainboard-Mapping für {filename}: {e}")
                return

        # 2. CPU CHECK
        elif "speicher-controller" in root_keys or "prozessor" in root_keys:
            try:
                marvin_json = self.map_cpu(data, html_content)
                found_category = True
                cat_debug = "Prozessor"
            except Exception as e:
                print(f"   ❌ Fehler im CPU-Mapping für {filename}: {e}")
                return

        # 3. GPU CHECK
        elif "systemanforderungen" in root_keys and "grafikprozessor" in allgemein_str:
            try:
                marvin_json = self.map_gpu(data, html_content)
                found_category = True
                cat_debug = "Grafikkarte"
            except Exception as e:
                print(f"   ❌ Fehler im GPU-Mapping für {filename}: {e}")
                return

        # 4. RAM CHECK
        elif "arbeitsspeicher" in root_keys and "grafikprozessor" not in allgemein_str:
             try:
                marvin_json = self.map_ram(data, html_content)
                found_category = True
                cat_debug = "RAM"
             except Exception as e:
                print(f"   ❌ Fehler im RAM-Mapping für {filename}: {e}")
                return
        
        # 5. GEHÄUSE / CASE CHECK
        elif "kühlsystem (installiert)" in root_keys or "gehäuse" in allgemein_str or "midi tower" in allgemein_str:
             try:
                marvin_json = self.map_case(data, html_content)
                found_category = True
                cat_debug = "Gehäuse"
             except Exception as e:
                print(f"   ❌ Fehler im Case-Mapping für {filename}: {e}")
                return
         
        # 6. NETZTEIL CHECK
        elif "stromversorgungsgerät" in root_keys or "netzteil" in allgemein_str:
             try:
                marvin_json = self.map_psu(data, html_content)
                found_category = True
                cat_debug = "Netzteil"
             except Exception as e:
                print(f"   ❌ Fehler im PSU-Mapping für {filename}: {e}")
                return 
            
        # 7. STORAGE CHECK (SSD / HDD)
        # Hier nutzen wir json_str, deshalb muss es oben definiert sein!
        elif "festplatte" in root_keys or "ssd" in json_str or "hdd" in json_str or "kapazität" in allgemein_str:
             try:
                marvin_json = self.map_storage(data, html_content)
                found_category = True
                cat_debug = "Speicher"
             except Exception as e:
                print(f"   ❌ Fehler im Storage-Mapping für {filename}: {e}")
                return    
        
        # 8. MONITOR CHECK
        elif "bildschirm" in root_keys or "display" in root_keys or "monitor" in allgemein_str:
             try:
                marvin_json = self.map_monitor(data, html_content)
                found_category = True
                cat_debug = "Monitor"
             except Exception as e:
                print(f"   ❌ Fehler im Monitor-Mapping für {filename}: {e}")
                return
        
        # 9. LÜFTER / FAN CHECK (WG 11)
        elif "lüfter" in filename.lower() or "fan" in filename.lower() or \
             "gehäuselüfter" in json_str or \
             "rotationsgeschwindigkeit" in json_str or \
             "lüfterdurchmesser" in json_str:
             try:
                marvin_json = self.map_fan(data, html_content)
                found_category = True
                cat_debug = "Lüfter"
             except Exception as e:
                print(f"   ❌ Fehler im Fan-Mapping für {filename}: {e}")
                return
        
        # 10. CPU-KÜHLER CHECK (WG 9)
        elif "bauhöhe" in json_str or "radiatorgröße" in json_str or "kühler" in filename.lower():
             try:
                marvin_json = self.map_cpu_cooler(data, html_content)
                found_category = True
                cat_debug = "CPU-Kühler"
             except Exception as e:
                print(f"   ❌ Fehler im Kühler-Mapping für {filename}: {e}")
                return  
        
        else:
            print(f"   ⚠️ SKIPPED Marvin-JSON für {filename}: Keine bekannte Struktur erkannt.")
            return
       

        # Speichern
        if found_category:
            output_path = os.path.join(self.output_folder, filename.replace(".json", "_marvin.json"))
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(marvin_json, f, indent=4, ensure_ascii=False)
                
            print(f"   👤 Marvin-JSON erstellt ({cat_debug} | WG {marvin_json.get('kWarengruppe')}): {output_path}")
            
            
            