import json
import os
import re

class MarvinMapper:
    def __init__(self, output_folder="output_JSON_Marvin"):
        self.output_folder = output_folder
        if not os.path.exists(output_folder):
            os.makedirs(output_folder)

    def safe_str(self, val):
        """Macht jeden Wert sicher zum String"""
        if val is None: return ""
        if isinstance(val, (list, dict)): return json.dumps(val, ensure_ascii=False)
        return str(val).strip()

    def extract_number(self, text):
        """Holt die erste Ganzzahl (Integer) aus einem String"""
        if not text or str(text) == "N/A": return 0
        clean_text = self.safe_str(text).replace('.', '').replace(',', '.')
        match = re.search(r'(\d+)', clean_text)
        return int(match.group(1)) if match else 0

    def extract_float(self, text):
        """Holt eine Kommazahl (Float) aus einem String"""
        if not text or str(text) == "N/A": return 0.0
        clean_text = self.safe_str(text).replace(',', '.')
        match = re.search(r'(\d+\.\d+|\d+)', clean_text)
        return float(match.group(1)) if match else 0.0

    def clean_brand_name(self, full_name, remove_list):
        """Bereinigt den Namen"""
        clean = self.safe_str(full_name)
        for item in remove_list:
            if item:
                # Escape Special Chars um Regex-Fehler zu vermeiden
                clean = re.sub(fr'\b{re.escape(str(item))}\b', '', clean, flags=re.IGNORECASE)
        
        patterns = [r'- Kit -', r'\bKit\b', r'^\W+', r'\W+$', r'\s+GB\s+', r'\s+MHz\s+', r'Prozessor']
        for p in patterns:
            clean = re.sub(p, ' ', clean, flags=re.IGNORECASE)
        return " ".join(clean.split())
    
    def _extract_value_with_unit(self, text, unit_regex):
        if not text: return 0.0
        pattern = fr'(\d+([.,]\d+)?)\s*({unit_regex})'
        match = re.search(pattern, self.safe_str(text), re.IGNORECASE)
        if match:
            val_str = match.group(1).replace(',', '.')
            return float(val_str)
        return 0.0
    
    def get_val_anywhere(self, data, keys_to_search, json_key):
        """Sucht einen Key in mehreren JSON-Bereichen (z.B. Technische Daten ODER Leistungen)"""
        for area in keys_to_search:
            block = data.get(area, {})
            if block and json_key in block:
                return str(block[json_key]).strip()
        return ""

    # ==========================================
    # 🐏 RAM MAPPER 
    # ==========================================
    def map_ram(self, data, html_content=""):
        allgemein = data.get("Allgemein", {})
        speicher = data.get("Arbeitsspeicher", {}) or data.get("Speicher", {}) # Fallback
        p_name = data.get("Produktname", "")

        kap = allgemein.get("Kapazität", "0")
        takt = speicher.get("Geschwindigkeit", "0")
        lat = speicher.get("Latenzzeiten", "0")
        typ = speicher.get("Technologie", "")

        mem_size = self.extract_number(kap)
        clock = self.extract_number(takt)
        cl = self.extract_number(lat)
        
        is_ddr5 = "DDR5" in self.safe_str(typ).upper()
        mem_type = "DDR5" if is_ddr5 else "DDR4"
        
        slots = 1
        match = re.search(r'(\d+)\s*x', self.safe_str(kap))
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
        allg = data.get("Allgemein", {})
        cpu = data.get("Prozessor", {})
        mem = data.get("Speicher-Controller", {})
        
        p_name = data.get("Produktname", data.get("_Produktname", ""))
        
        is_intel = "INTEL" in str(p_name).upper() or "CORE" in str(allg.get("Serie", "")).upper()
        k_warengruppe = 8 if is_intel else 7
        
        sockel_raw = self.safe_str(cpu.get("Sockel", ""))
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
        if p_cores == 0: p_cores = cores_total

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

        chipsatz_komp = cpu.get("Chipsatz-Kompatibilität", "N/A")
        if chipsatz_komp == "N/A" or not chipsatz_komp:
            chipsatz_komp = sockel_clean

        modell = str(allg.get("Modell", "")).replace("Prozessor", "").strip()
        serie = allg.get("Serie", "")
        short_name = f"{serie} {modell} {cores_total}-Core"
        if is_intel and e_cores > 0:
            short_name += f" ({p_cores}P+{e_cores}E)"
        
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
            "mainboard_cpu_chipsatz": chipsatz_komp,
            "konfiggruppen_typ": "Prozessor"
        }

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
        allg = data.get("Allgemein", {})
        mem = data.get("Arbeitsspeicher", {})
        sys = data.get("Systemanforderungen", {})
        dims = data.get("Abmessungen und Gewicht", {})
        p_name = data.get("Produktname", data.get("_Produktname", ""))

        hersteller_raw = self.safe_str(allg.get("Chipsatz-Hersteller", ""))
        chipset_man = "Nvidia" if "NVIDIA" in hersteller_raw.upper() else ("AMD" if "AMD" in hersteller_raw.upper() else "Intel")
        
        chip = allg.get("Grafikprozessor", "")
        vram_gb = self.extract_number(mem.get("Grösse", "0"))
        mem_tech_raw = self.safe_str(mem.get("Technologie", "")).upper()
        
        mem_tech = "-1"
        if "GDDR7" in mem_tech_raw: mem_tech = "GDDR7"
        elif "GDDR6X" in mem_tech_raw: mem_tech = "GDDR6X"
        elif "GDDR6" in mem_tech_raw: mem_tech = "GDDR6"
        elif "GDDR5" in mem_tech_raw: mem_tech = "GDDR5"
        
        psu_req = self.extract_number(sys.get("Erforderliche Leistungsversorgung", "0"))
        
        tdp = self.extract_number(sys.get("Stromverbrauch (TDP)", "0"))
        if tdp == 0: tdp = self.extract_number(sys.get("Leistungsaufnahme", "0"))
        if tdp == 0: tdp = self.extract_number(sys.get("TGP", "0"))
        
        length = self.extract_number(dims.get("Tiefe", "0"))
        width = self.extract_number(dims.get("Breite", "0"))
        height = self.extract_number(dims.get("Höhe", "0"))
        
        if length < 50 and length > 0: length *= 10
        if width < 50 and width > 0: width *= 10
        if height < 50 and height > 0: height *= 10

        connectors = sys.get("Zusätzliche Anforderungen", "")
        dx_val = "12 Ultimate" if "12" in self.safe_str(allg.get("API-Unterstützung", "")) else "12"

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
        allg = data.get("Allgemein", {})
        ram = data.get("Unterstützter RAM", {})
        conn = data.get("Erweiterung / Konnektivität", {}) or data.get("Erweiterung/Konnektivität", {})
        audio = data.get("Audio", {})
        lan = data.get("LAN", {})
        specials = data.get("Besonderheiten", {})
        p_name = data.get("Produktname", data.get("_Produktname", ""))

        def count_in_string(text, keywords):
            if not text or str(text) == "N/A": return 0
            count = 0
            parts = re.split(r'[¦,\n\+]| plus ', str(text), flags=re.IGNORECASE)
            for part in parts:
                part = part.strip()
                if any(k.lower() in part.lower() for k in keywords):
                    match = re.search(r'^(\d+)\s*[xX]', part)
                    if match: count += int(match.group(1))
                    else: count += 1 
            return count

        sockel_raw = self.safe_str(allg.get("Prozessorsockel", ""))
        sockel = sockel_raw
        if "AM5" in sockel_raw.upper(): sockel = "AM5"
        elif "AM4" in sockel_raw.upper(): sockel = "AM4"
        elif "1700" in sockel_raw: sockel = "LGA1700"
        elif "1851" in sockel_raw: sockel = "LGA1851"
        
        chipsatz = self.safe_str(allg.get("Chipsatz", "")).replace("AMD", "").replace("Intel", "").strip()
        
        formfaktor_raw = self.safe_str(allg.get("Produkttyp", ""))
        formfaktor = "ATX"
        if "micro" in formfaktor_raw.lower() or "mATX" in formfaktor_raw: formfaktor = "mATX"
        elif "mini-itx" in formfaktor_raw.lower() or "m-itx" in formfaktor_raw.lower(): formfaktor = "ITX"
        elif "e-atx" in formfaktor_raw.lower(): formfaktor = "E-ATX"

        mem_tech = self.safe_str(ram.get("Technologie", "DDR4"))
        if "DDR5" in mem_tech.upper(): mem_tech = "DDR5"
        elif "DDR4" in mem_tech.upper(): mem_tech = "DDR4"
        
        mem_slots = self.extract_number(ram.get("Anzahl Steckplätze", "0"))
        if mem_slots == 0:
            if formfaktor == "ITX": mem_slots = 2
            else: mem_slots = 4
        
        mem_max = self.extract_number(ram.get("Max. Größe", "0"))
        
        bustakt_str = self.safe_str(ram.get("Bustakt", "0"))
        all_speeds = re.findall(r'(\d{4})', bustakt_str)
        max_speed = 0
        if all_speeds: max_speed = max([int(s) for s in all_speeds])
            
        ddr5_clock = max_speed if mem_tech == "DDR5" else 0
        ddr4_clock = max_speed if mem_tech == "DDR4" else 0

        ports_back = self.safe_str(conn.get("Schnittstellen (Rückseite)", ""))
        ports_internal = self.safe_str(conn.get("Schnittstellen (Intern)", "")) + self.safe_str(conn.get("Schnittstellen", ""))
        storage = self.safe_str(conn.get("Speicherschnittstellen", ""))
        slots_str = self.safe_str(conn.get("Erweiterungssteckplätze", ""))
        
        usb_back_count = count_in_string(ports_back, ["USB"])
        hdmi_count = count_in_string(ports_back, ["HDMI"])
        dp_count = count_in_string(ports_back, ["DisplayPort"])
        
        lan_count = count_in_string(ports_back, ["LAN", "RJ-45", "Ethernet"])
        has_lan_chip = "LAN" in self.safe_str(lan.get("Netzwerkcontroller", ""))
        if lan_count == 0 and has_lan_chip: lan_count = 1

        audio_jacks = count_in_string(ports_back, ["Audio", "Line-Out", "Microphone", "Jack"])
        if audio_jacks == 0 and "Audio" in self.safe_str(audio.get("Audio Codec", "")): audio_jacks = 3
        
        sata_count = count_in_string(storage, ["SATA"])
        if sata_count == 0 and formfaktor != "ITX": sata_count = 4

        m2_count = count_in_string(storage, ["M.2"])
        pcie_count = count_in_string(slots_str, ["PCI Express", "PCIe"])
        
        kw_rgb_4pin = ["RGB LED", "JRGB", "RGB_HEADER", "RGB 12V", "LED_C"]
        rgb_header = count_in_string(ports_internal, kw_rgb_4pin)
        
        kw_argb_3pin = ["ARGB", "Addressable", "Gen 2", "JRAINBOW", "JARGB", "ADD_GEN", "A_RGB", "AD_RGB"]
        argb_header = count_in_string(ports_internal, kw_argb_3pin)
        
        kw_pump = ["Pump", "AIO", "Water", "W_PUMP", "WP", "SYS_FAN_PUMP", "PUMP_SYS"]
        aio_pump = count_in_string(ports_internal, kw_pump)
        
        wakue_anschluss = 1 if aio_pump > 0 or count_in_string(ports_internal, ["Flow", "Durchfluss"]) > 0 else 0

        has_onboard_rgb = 0 
        feature_text = str(specials) + str(allg)
        if "Onboard LED" in feature_text or "Beleuchtungszone" in feature_text:
            has_onboard_rgb = 1
            
        has_wlan = 1 if "Wi-Fi" in str(lan.get("Netzwerkschnittstellen", "")) or "WLAN" in str(lan.get("Netzwerkschnittstellen", "")) else 0
        has_bt = 1 if "Bluetooth" in str(lan.get("Netzwerkschnittstellen", "")) else 0
        
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
                "audioChipset": self.safe_str(audio.get("Audio Codec", "N/A")),
                "audioChannels": "7.1" if "7.1" in str(audio.get("Typ", "")) else "5.1",
                "ethernetController": self.safe_str(lan.get("Netzwerkcontroller", "N/A")),
                "wlan": has_wlan,
                "bluetooth": has_bt,
                "board_wlan": has_wlan,
                "rgb": has_onboard_rgb,             
                "argb": 1 if argb_header > 0 else 0, 
                "rgb_anschluss_4pin_rgb": rgb_header,
                "rgb_anschluss_3pin_argb": argb_header,
                "aioPump": 1 if aio_pump > 0 else 0, 
                "board_wakue_anschluss": wakue_anschluss, 
                "tower_board_bauform": tower_form,
                "board_netzteil_p8": has_p8,
                "board_netzteil_p4": 0,
                "mainboard_cpu_chipsatz": chipsatz,
                "board_cpukuehler_sockel": sockel,
                "konfiggruppen_typ": "Mainboard"
            }
        }
        
    def map_psu(self, data, html_content=""):
        allg = data.get("Allgemein", {})
        strom = data.get("Stromversorgungsgerät", {})
        vers = data.get("Verschiedenes", {})
        p_name = data.get("Produktname", "")

        watt = self.extract_number(strom.get("Leistungskapazität", "0"))
        fan_str = self.safe_str(vers.get("Kühlsystem", "")) 
        fan_mm = self.extract_number(fan_str)
        if fan_mm > 0 and fan_mm < 20: fan_mm *= 10
        if fan_mm == 0: fan_mm = 120 

        cert_raw = self.safe_str(strom.get("80-PLUS-Zertifizierung", "")).upper()
        cert_str = "Standard"
        cert_int = 0
        
        if "TITANIUM" in cert_raw: cert_str, cert_int = "TITANIUM", 5
        elif "PLATINUM" in cert_raw: cert_str, cert_int = "PLATINUM", 4
        elif "GOLD" in cert_raw: cert_str, cert_int = "GOLD", 3
        elif "SILVER" in cert_raw: cert_str, cert_int = "SILVER", 2
        elif "BRONZE" in cert_raw: cert_str, cert_int = "BRONZE", 1
        elif "80 PLUS" in cert_raw: cert_str, cert_int = "Standard", 0

        conns = self.safe_str(strom.get("Angaben zu Ausgangsleistungsanschlüssen", ""))
        
        has_p8 = 1 if "EPS" in conns or "CPU" in conns else 1
        has_p4 = 1 if "4-polig" in conns and "ATX12V" in conns else 0
        
        pcie_count = 0
        conn_parts = re.split(r'[¦,\n]', conns)
        for part in conn_parts:
            if "PCI" in part or "GPU" in part or "Grafik" in part:
                match = re.search(r'(\d+)\s*x', part)
                if match:
                    pcie_count += int(match.group(1))
        
        if pcie_count == 0:
            if watt >= 1000: pcie_count = 6
            elif watt >= 850: pcie_count = 4
            elif watt >= 650: pcie_count = 2
            elif watt >= 450: pcie_count = 1
            
        pcie_str = f"{pcie_count}x 6+2-Pin" if pcie_count > 0 else "N/A"

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
        allg = data.get("Allgemein", {})
        cool_in = data.get("Kühlsystem (Installiert)", {})
        cool_sup = data.get("Kühlsystem (Unterstützt)", {})
        sys_req = data.get("Systemanforderungen", {})
        dims = data.get("Abmessungen und Gewicht", {})
        p_name = data.get("Produktname", data.get("_Produktname", ""))

        width = self.extract_number(dims.get("Breite", "0"))
        height = self.extract_number(dims.get("Höhe", "0"))
        length = self.extract_number(dims.get("Tiefe", "0")) 
        
        if width < 100 and width > 0: width *= 10
        if height < 100 and height > 0: height *= 10
        if length < 100 and length > 0: length *= 10

        gpu_max = self.extract_number(sys_req.get("Max. Länge Grafikkarte", "0"))
        cpu_max = self.extract_number(sys_req.get("Max. Höhe CPU-Kühler", "0"))
        
        mb_support = self.safe_str(allg.get("Unterstützte Mainboards", "")) + self.safe_str(allg.get("Max. Mainboard-Größe", ""))
        
        tower_form = 1 
        form_str = "ITX"
        
        if "E-ATX" in mb_support or "Extended ATX" in mb_support:
            tower_form = 3
            form_str = "ATX" 
        elif "ATX" in mb_support: 
            tower_form = 3
            form_str = "ATX"
        elif "Micro-ATX" in mb_support or "mATX" in mb_support:
            tower_form = 2
            form_str = "mATX"
            
        def count_fans(text_dict):
            total = 0
            if not isinstance(text_dict, dict): return 0
            for val in text_dict.values():
                match = re.search(r'(\d+)\s*x', str(val))
                if match:
                    total += int(match.group(1))
            return total

        fans_inc = count_fans(cool_in)
        fans_max = self.extract_number(cool_sup.get("Lüfterhalterungen (Gesamt)", "0"))
        if fans_max == 0: fans_max = fans_inc + 2 

        rad_front = self.extract_number(cool_sup.get("Radiatorgröße (Vorne)", "0"))
        rad_top = self.extract_number(cool_sup.get("Radiatorgröße (Oben)", "0"))
        aio_max = max(rad_front, rad_top)
        
        aio_val = "0"
        if aio_max >= 360: aio_val = "360"
        elif aio_max >= 240: aio_val = "240"
        elif aio_max >= 120: aio_val = "120"

        has_rgb = 1 if "RGB" in str(cool_in) or "RGB" in self.safe_str(allg.get("Besonderheiten", "")) else 0
        is_silent = 1 if "Dämmung" in self.safe_str(allg.get("Besonderheiten", "")) or "Silent" in p_name else 0
        
        color = allg.get("Farbe", "Schwarz") 

        brand_clean = self.clean_brand_name(p_name, ["Gehäuse", "Tower", "Midi", "Case", form_str])
        short_name = f"{form_str} {brand_clean} {color}"

        return {
            "kWarengruppe": 3,
            "Attribute": {
                "shortNameLang": short_name,
                "formFactor": form_str, 
                "tower_board_bauform": tower_form, 
                "width": width,
                "height": height,
                "length": length,
                "tower_grafik_groesse": gpu_max, 
                "cpukuehler_bauhoehe": cpu_max,  
                "fansInc": fans_inc,
                "fansMax": fans_max,
                "aioSlots": aio_val, 
                "wakue_slots": 1 if aio_max > 0 else 0, 
                "rgb": has_rgb,
                "silent": is_silent,
                "color": color,
                "tower_lw_slots": 0, 
                "low_profile": 0,
                "konfiggruppen_typ": "Gehäuse",
                "upgradeArticle": 1,
                "Seriennummer": 1,
                "markup": 0,
                "Hardware": 0
            }
        }
        
    def map_storage(self, data, html_content=""):
        allg = data.get("Allgemein", {})
        perf = data.get("Leistung", {})
        p_name = data.get("Produktname", data.get("_Produktname", ""))
        form = self.safe_str(allg.get("Formfaktor", ""))
        interf = self.safe_str(allg.get("Schnittstelle", ""))
        dev_type = self.safe_str(allg.get("Gerätetyp", ""))
        
        disk_type = "SSD"
        if "HDD" in dev_type or "Festplatte" in dev_type or "7200" in str(perf.get("Spindelgeschwindigkeit", "")):
            disk_type = "HDD"
        elif "M.2" in form:
            if "NVMe" in interf or "PCI" in interf: disk_type = "M.2 NVMe"
            else: disk_type = "M.2 SATA"
        elif "2.5" in form:
            disk_type = "SSD"

        cap_raw = self.safe_str(allg.get("Kapazität", "0"))
        cap_gb = 0
        match_tb = re.search(r'(\d+)\s*TB', cap_raw, re.IGNORECASE)
        if match_tb: cap_gb = int(match_tb.group(1)) * 1000
        else:
            match_gb = re.search(r'(\d+)', cap_raw)
            if match_gb: cap_gb = int(match_gb.group(1))

        def get_speed(val):
            if not val or val == "N/A": return 0
            val_str = str(val).upper()
            is_gb = "GB" in val_str
            num = self.extract_float(val_str)
            
            speed = int(num * 1000) if is_gb else int(num)
            if speed < 100 and disk_type != "HDD":
                return 0 
            return speed

        read_speed = get_speed(perf.get("Interner Datendurchsatz (Lesen)", "0"))
        write_speed = get_speed(perf.get("Interner Datendurchsatz (Schreiben)", "0"))
        
        if read_speed < 500 and disk_type == "M.2 NVMe": read_speed = 3500

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
        allg = data.get("Allgemein", {})
        disp = data.get("Display", {})
        conn = data.get("Schnittstellen", {})
        p_name = data.get("Produktname", data.get("_Produktname", ""))

        diag_str = self.safe_str(disp.get("Diagonale", ""))
        inch = 24.0 # Fallback
        match_inch = re.search(r'(\d{2,3}(\.\d)?)', diag_str)
        if match_inch:
            inch = float(match_inch.group(1))

        res_raw = self.safe_str(disp.get("Auflösung", ""))
        res_match = re.search(r'(\d{3,4})\s*[xX]\s*(\d{3,4})', res_raw)
        
        resolution = "1920x1080"
        if res_match:
            w = res_match.group(1)
            h = res_match.group(2)
            resolution = f"{w}x{h}"

        ports_str = self.safe_str(conn.get("Anschlüsse", ""))
        
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

        panel = self.safe_str(disp.get("Panel-Typ", "")).replace("Panel", "").strip()
        if len(panel) > 10: panel = "" 
        
        remove_list = [
            "Monitor", "TFT", "Display", "Zoll", str(int(inch)), resolution, 
            "LED", "LCD", "Gaming", "Screen", "cm", "Backlight", "hintergrundbeleuchteter"
        ]
        
        match_cm = re.search(r'(\d+(\.\d)?)\s*cm', p_name)
        if match_cm: 
            remove_list.append(match_cm.group(0)) 
            remove_list.append(match_cm.group(1)) 

        brand_clean = self.clean_brand_name(p_name, remove_list)
        
        brand_clean = re.sub(r'[-–]\s*[-–]', '', brand_clean) 
        brand_clean = re.sub(r'^\W+|\W+$', '', brand_clean)   
        brand_clean = re.sub(r'\(\s*\)', '', brand_clean)     
        
        hz_str = self.safe_str(disp.get("Bildwiederholrate", ""))
        hz = self.extract_number(hz_str)
        hz_info = f"{hz}Hz" if hz > 60 else ""
        
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
        allg = data.get("Allgemein", {})
        tech = data.get("Technische Daten", {})
        feat = data.get("Anschlüsse & Features", {})
        p_name = data.get("Produktname", data.get("_Produktname", ""))

        size_str = self.safe_str(tech.get("Lüfterdurchmesser", ""))
        size = "120" # Fallback
        match_size = re.search(r'(\d{2,3})', size_str)
        if match_size:
            size = match_size.group(1)

        is_pwm = "PWM" in self.safe_str(feat.get("Stromanschluss", "")).upper() or "PWM" in p_name.upper()
        
        rgb_str = self.safe_str(feat.get("Beleuchtung", "")).upper()
        is_argb = "ARGB" in rgb_str or "ADDRESSABLE" in rgb_str
        is_rgb = "RGB" in rgb_str and not is_argb
        
        pack_qty = self.extract_number(allg.get("Paketmenge", "1"))
        pack_str = ""
        if pack_qty > 1:
            pack_str = f"{pack_qty}er-Pack"
        
        attrs = []
        if is_argb: attrs.append("ARGB")
        elif is_rgb: attrs.append("RGB")
        if is_pwm: attrs.append("PWM")
        
        color = self.safe_str(allg.get("Farbe", ""))
        if color and color.lower() not in ["schwarz", "n/a"]: 
            attrs.append(color)
            
        attr_string = " ".join(attrs)
        
        p_name_clean = re.sub(r'\d+\s*[xX]\s*\d+', '', p_name)
        
        remove_list = [
            "Gehäuselüfter", "Fan", "Lüfter", "Cooling", "Case", 
            size + "mm", size + " mm", size, 
            "PWM", "RGB", "ARGB", "LED", "Neutral",
            pack_str, "Pack", "Kit", "Triple", "Duo"
        ]
        
        brand_clean = self.clean_brand_name(p_name_clean, remove_list)
        
        brand_clean = re.sub(r'[-–]\s*[-–]', '', brand_clean)
        brand_clean = re.sub(r'^\W+|\W+$', '', brand_clean)
        
        short_name = f"{size}mm {brand_clean} {attr_string} {pack_str}".strip()
        short_name = " ".join(short_name.split()) 

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
        allg = data.get("Allgemein", {})
        komp = data.get("Kompatibilität", {})
        tech = data.get("Technische Daten", {})
        feat = data.get("Beleuchtung & Features", {})
        p_name = data.get("Produktname", data.get("_Produktname", ""))

        is_aio = "aio" in str(allg).lower() or "wasser" in str(allg).lower() or "liquid" in p_name.lower()
        
        height_mm = self._extract_value_with_unit(tech.get("Bauhöhe (nur Kühler)", ""), "mm")
        rad_size = self._extract_value_with_unit(tech.get("Radiatorgröße", ""), "mm")

        if is_aio and height_mm == 0: height_mm = 55 
            
        sockets_str = self.safe_str(komp.get("Sockel", ""))
        sockets_clean = sockets_str.replace("[", "").replace("]", "").replace("'", "")
        
        has_amd = "AM" in sockets_clean.upper() or "FM" in sockets_clean.upper()
        has_intel = "LGA" in sockets_clean.upper() or "1700" in sockets_clean or "1200" in sockets_clean
        
        cpu_kuehler_typ = 0
        if has_amd and has_intel: cpu_kuehler_typ = 3
        elif has_intel: cpu_kuehler_typ = 2
        elif has_amd: cpu_kuehler_typ = 1
        
        rgb_text = str(feat) + " " + p_name
        has_rgb = 1 if "RGB" in rgb_text else 0
        has_argb = 1 if "ARGB" in rgb_text or "Addressable" in rgb_text else 0
        is_silent = 1 if "silent" in str(data).lower() or "quiet" in p_name.lower() else 0
        
        tdp = int(self._extract_value_with_unit(allg.get("TDP-Klasse", ""), "W|Watt"))
        
        suffix = ""
        if is_aio and rad_size > 0: suffix = f"{int(rad_size)}mm AiO"
        elif tdp > 0: suffix = f"{tdp}W TDP"
            
        remove_list = ["CPU-Kühler", "Cooler", "Wasserkühlung", "Liquid", "All-in-One", "TDP", "Watt", "System", "Komplett"]
        brand_clean = self.clean_brand_name(p_name, remove_list)
        short_name = f"{brand_clean} {suffix}".strip()
        
        return {
            "kWarengruppe": 9,
            "Attribute": {
                "shortNameLang": short_name,
                "cpukuehler_bauhoehe": int(height_mm),
                "tdp": tdp,
                "rgb": has_rgb,
                "argb": has_argb,
                "rgb_anschluss_4pin_rgb": has_rgb,    
                "rgb_anschluss_3pin_argb": has_argb, 
                "cpukuehler_typ": cpu_kuehler_typ,
                "board_cpukuehler_sockel": sockets_clean[:255], 
                "cpukuehler_breite": 1,
                "silent": is_silent,
                "konfiggruppen_typ": "CPU-Kühler",
                "Seriennummer": 1,
                "upgradeArticle": 1,
                "markup": 0,
                "Hardware": 0
            }
        }  
    
    def map_cooler_wg12(self, data, html_content=""):
        komp = data.get("Kompatibilität", {})
        tech = data.get("Technische Daten", {})
        p_name = data.get("Produktname", "")

        height_mm = self._extract_value_with_unit(tech.get("Bauhöhe (nur Kühler)", ""), "mm")
        
        sockets_str = self.safe_str(komp.get("Sockel", ""))
        sockets_clean = sockets_str.replace("[", "").replace("]", "").replace("'", "")
        
        has_amd = "AM" in sockets_clean.upper() or "FM" in sockets_clean.upper()
        has_intel = "LGA" in sockets_clean.upper() or "1700" in sockets_clean or "1200" in sockets_clean
        
        cpu_kuehler_typ = 0
        if has_amd and has_intel: cpu_kuehler_typ = 3
        elif has_intel: cpu_kuehler_typ = 2
        elif has_amd: cpu_kuehler_typ = 1

        remove_list = ["Kühler", "Cooler", "CPU", "Prozessor"]
        brand_clean = self.clean_brand_name(p_name, remove_list)
        short_name = f"{brand_clean} {int(height_mm)}mm".strip()

        return {
            "kWarengruppe": 12, 
            "Attribute": {
                "shortNameLang": short_name,
                "cpukuehler_bauhoehe": int(height_mm),
                "cpukuehler_breite": 1, 
                "cpukuehler_typ": cpu_kuehler_typ,
                "board_cpukuehler_sockel": sockets_clean[:255],
                "konfiggruppen_typ": "Kühler",
                "Seriennummer": 1,
                "upgradeArticle": 1,
                "markup": 0,
                "Hardware": 0
            }
        }  
        
    def map_input_devices_wg14(self, data, html_content=""):
        allg = data.get("Allgemein", {})
        conn = data.get("Konnektivität", {})
        tech = data.get("Technische Daten", {})
        p_name = data.get("Produktname", "")
        
        dev_type = allg.get("Gerätetyp", "Eingabegerät")
        connection = self.safe_str(conn.get("Anschlusstechnik", ""))
        interface = self.safe_str(conn.get("Schnittstelle", ""))
        layout = self.safe_str(tech.get("Layout", ""))
        color = self.safe_str(allg.get("Farbe", ""))
        
        features = []
        
        if "kabellos" in connection.lower() or "wireless" in connection.lower() or "bluetooth" in connection.lower() or "bluetooth" in interface.lower():
            features.append("Wireless")
        elif "verkabelt" in connection.lower() or "usb" in connection.lower() or "kabel" in connection.lower():
            features.append("USB")
            
        if "Deutsch" in layout or "DE" in layout or "QWERTZ" in layout:
            features.append("DE")
        elif "US" in layout or "QWERTY" in layout:
            features.append("US")
            
        if color and color != "N/A":
            features.append(color)

        feature_str = " ".join(features)
        
        remove_list = ["Eingabegerät", "Tastatur", "Maus", "Keyboard", "Mouse", "Gaming", "Desktop", "Set"]
        brand_clean = self.clean_brand_name(p_name, remove_list)
        
        short_name = f"{brand_clean} {dev_type} {feature_str}".strip()
        short_name = re.sub(r'\s+', ' ', short_name)

        return {
            "kWarengruppe": 14, 
            "Attribute": {
                "shortNameLang": short_name,
                "konfiggruppen_typ": "Eingabegeräte",
                "Seriennummer": 1,
                "upgradeArticle": 1,
                "markup": 0,
                "Hardware": 0
            }
        } 
        
    def map_cables_wg15(self, data, html_content=""):
        allg = data.get("Allgemein", {})
        tech = data.get("Technische Daten", {})
        p_name = data.get("Produktname", "")

        typ = allg.get("Gerätetyp", "Kabel")
        conn_a = self.safe_str(tech.get("Anschluss A", ""))
        conn_b = self.safe_str(tech.get("Anschluss B", ""))
        length = self.safe_str(tech.get("Länge", ""))
        standard = self.safe_str(tech.get("Standard", ""))
        color = self.safe_str(allg.get("Farbe", ""))

        conn_str = ""
        if conn_a and conn_b and conn_a != "N/A":
            c_a_clean = conn_a.replace("Anschluss", "").strip()
            c_b_clean = conn_b.replace("Anschluss", "").strip()
            conn_str = f"{c_a_clean} auf {c_b_clean}"
        elif conn_a and conn_a != "N/A":
            conn_str = conn_a
            
        len_str = ""
        if length and length != "N/A":
            len_str = length.replace(" ", "")
            
        std_str = ""
        if standard and standard != "N/A":
            std_str = standard

        remove_list = ["Kabel", "Adapter", "Verbindungskabel", "Anschlusskabel"]
        brand_clean = self.clean_brand_name(p_name, remove_list)
        
        parts = [brand_clean, conn_str, len_str, std_str, typ, color]
        parts_clean = [p for p in parts if p and "N/A" not in p]
        
        short_name = " ".join(parts_clean).strip()
        short_name = re.sub(r'\s+', ' ', short_name)

        return {
            "kWarengruppe": 15,
            "Attribute": {
                "shortNameLang": short_name,
                "konfiggruppen_typ": "Kabel/Adapter",
                "Seriennummer": 0,
                "upgradeArticle": 1,
                "markup": 0,
                "Hardware": 0
            }
        }  
        
    def map_soundcard_wg16(self, data, html_content=""):
        allg = data.get("Allgemein", {})
        audio = data.get("Audio", {})
        tech = data.get("Technische Daten", {})
        p_name = data.get("Produktname", "")

        lp_str = self.safe_str(tech.get("Low Profile", "")).lower()
        is_lp = 1 if "ja" in lp_str or "yes" in lp_str or "low profile" in p_name.lower() or "lp" in p_name.lower().split() else 0

        interface = self.safe_str(allg.get("Schnittstelle", ""))
        if "express" in interface.lower(): interface = "PCIe"
        if "usb" in interface.lower(): interface = "USB"

        channels = self.safe_str(audio.get("Soundmodus", ""))
        chan_short = ""
        if "7.1" in channels: chan_short = "7.1"
        elif "5.1" in channels: chan_short = "5.1"
        elif "stereo" in channels.lower(): chan_short = "Stereo"

        remove_list = ["Soundkarte", "Audio", "Interface", "Internal", "External", "Hi-Res", "Gaming", "PCIe", "USB", "Sound", "Card"]
        brand_clean = self.clean_brand_name(p_name, remove_list)

        short_name = f"{brand_clean} {interface} {chan_short}".strip()
        short_name = re.sub(r'\s+', ' ', short_name)

        return {
            "kWarengruppe": 16,
            "Attribute": {
                "shortNameLang": short_name,
                "low_profile": is_lp,
                "konfiggruppen_typ": "Soundkarten",
                "Seriennummer": 1,
                "upgradeArticle": 1,
                "markup": 0,
                "Hardware": 0
            }
        } 
        
    def map_audio_wg17(self, data, html_content=""):
        allg = data.get("Allgemein", {})
        tech = data.get("Technische Daten", {})
        p_name = data.get("Produktname", "")

        lp_str = self.safe_str(tech.get("Low Profile", "")).lower()
        is_lp = 1 if "ja" in lp_str or "yes" in lp_str or "low profile" in p_name.lower() else 0

        dev_type = allg.get("Gerätetyp", "Audio-Gerät")
        interface = self.safe_str(tech.get("Schnittstelle", ""))
        
        if "USB" in interface: interface = "USB"
        elif "XLR" in interface: interface = "XLR"
        elif "PCI" in interface: interface = "PCIe"
        
        remove_list = ["Audio", "Gerät", "Mikrofon", "Microphone", "Interface", "USB", "XLR", "Kondensator", "Streaming"]
        brand_clean = self.clean_brand_name(p_name, remove_list)
        
        short_name = f"{brand_clean} {dev_type} {interface}".strip()
        short_name = re.sub(r'\s+', ' ', short_name)

        return {
            "kWarengruppe": 17,
            "Attribute": {
                "shortNameLang": short_name,
                "low_profile": is_lp,
                "konfiggruppen_typ": "Audio", 
                "Seriennummer": 1,
                "upgradeArticle": 1,
                "markup": 0,
                "Hardware": 0
            }
        }  
        
    def map_webcam_wg18(self, data, html_content=""):
        allg = data.get("Allgemein", {})
        video = data.get("Video", {})
        p_name = data.get("Produktname", "")

        res_str = self.safe_str(video.get("Max. Auflösung", "")).upper()
        res_short = ""
        if "4K" in res_str or "2160" in res_str: res_short = "4K"
        elif "1080" in res_str or "FULL HD" in res_str or "FHD" in res_str: res_short = "1080p"
        elif "720" in res_str or "HD" in res_str: res_short = "720p"
        
        fps_str = self.safe_str(video.get("Max. Bildrate", "")).lower()
        fps_short = ""
        if "60" in fps_str: fps_short = "60fps"
        elif "30" in fps_str: fps_short = "30fps"
        
        remove_list = ["Webcam", "Kamera", "Camera", "HD", "Full", "UHD", "Pro", "Stream"]
        brand_clean = self.clean_brand_name(p_name, remove_list)
        color = self.safe_str(allg.get("Farbe", ""))
        if color == "N/A": color = ""

        parts = [brand_clean, res_short, fps_short, "Webcam", color]
        parts_clean = [p for p in parts if p] 
        
        short_name = " ".join(parts_clean).strip()
        short_name = re.sub(r'\s+', ' ', short_name)

        return {
            "kWarengruppe": 18,
            "Attribute": {
                "shortNameLang": short_name,
                "konfiggruppen_typ": "Webcam",
                "Seriennummer": 1,
                "upgradeArticle": 1,
                "markup": 0,
                "Hardware": 0
            }
        }                  
    
    def map_gaming_chair_wg19(self, data, html_content=""):
        allg = data.get("Allgemein", {})
        mat = data.get("Materialien", {})
        tech = data.get("Technische Daten", {})
        p_name = data.get("Produktname", "")

        material = self.safe_str(mat.get("Bezug", "")).lower()
        mat_short = ""
        if "stoff" in material or "fabric" in material: mat_short = "Stoff"
        elif "kunstleder" in material or "pu" in material: mat_short = "Kunstleder"
        elif "echtleder" in material or "leder" in material: mat_short = "Echtleder"
        elif "mesh" in material: mat_short = "Mesh"
        else: mat_short = "Stoff/Kunstleder" 

        weight_load = self.safe_str(tech.get("Max. Belastbarkeit", ""))
        weight_short = ""
        match_w = re.search(r'(\d+)', weight_load)
        if match_w:
            weight_short = f"bis {match_w.group(1)}kg"
        
        color = allg.get("Farbe", "Schwarz")
        
        remove_list = ["Gaming", "Stuhl", "Chair", "Sitz", "Office", "Bürostuhl", "Series", "Edition"]
        brand_clean = self.clean_brand_name(p_name, remove_list)
        
        parts = [brand_clean, "Gaming Stuhl", mat_short, color, weight_short]
        parts_clean = [p for p in parts if p]
        
        short_name = " ".join(parts_clean).strip()
        short_name = re.sub(r'\s+', ' ', short_name)

        return {
            "kWarengruppe": 19,
            "Attribute": {
                "shortNameLang": short_name,
                "konfiggruppen_typ": "Gamingstuhl",
                "Seriennummer": 1,
                "upgradeArticle": 1,
                "markup": 0,
                "Hardware": 0
            }
        }
        
    def map_network_card_wg20(self, data, html_content=""):
        allg = data.get("Allgemein", {})
        p_name = data.get("Produktname", data.get("_Produktname", ""))
        
        # Bereiche wo Netzwerk-Daten stehen können
        search_areas = ["Technische Daten", "Netzwerk", "Anschlüsse und Schnittstellen"]

        # 1. Low Profile
        lp_str = self.get_val_anywhere(data, ["Technische Daten", "Allgemein"], "Low Profile").lower()
        is_lp = 1 if "ja" in lp_str or "yes" in lp_str or "low profile" in p_name.lower() else 0

        # 2. Geschwindigkeit
        # Suche nach "Übertragungsrate" ODER "Maximale Datenübertragungsrate"
        speed_raw = self.get_val_anywhere(data, search_areas, "Übertragungsrate").upper()
        if not speed_raw:
            speed_raw = self.get_val_anywhere(data, search_areas, "Maximale Datenübertragungsrate").upper()

        speed_short = ""
        if "10 G" in speed_raw or "10000 M" in speed_raw: speed_short = "10GbE"
        elif "2.5 G" in speed_raw or "2500 M" in speed_raw: speed_short = "2.5GbE"
        elif "1 G" in speed_raw or "1000 M" in speed_raw: speed_short = "1GbE"
        elif "300 MBIT" in speed_raw: speed_short = "300 Mbit/s" # Dein Beispiel 101745
        elif "150 MBIT" in speed_raw: speed_short = "150 Mbit/s" # Dein Beispiel 101744
        elif "WIFI" in speed_raw or "W-LAN" in p_name.upper(): speed_short = "WiFi"

        if "WIFI 7" in speed_raw or "WIFI 7" in p_name.upper(): speed_short = "WiFi 7"
        elif "WIFI 6E" in speed_raw or "WIFI 6E" in p_name.upper(): speed_short = "WiFi 6E"
        elif "WIFI 6" in speed_raw or "WIFI 6" in p_name.upper(): speed_short = "WiFi 6"

        # 3. Schnittstelle
        interface_raw = self.get_val_anywhere(data, search_areas, "Schnittstelle").upper()
        if not interface_raw:
             interface_raw = self.get_val_anywhere(data, search_areas, "Hostschnittstelle").upper() # Dein Beispiel
             
        interface_short = "PCIe" if "PCI" in interface_raw else ("USB" if "USB" in interface_raw else "")

        # 4. Port Typ
        port_raw = self.get_val_anywhere(data, search_areas, "Anschlusstyp").upper()
        port_short = ""
        if "SFP" in port_raw: port_short = "SFP+"
        elif "RJ45" in port_raw or "RJ-45" in port_raw: port_short = "RJ45"
        
        remove_list = ["Netzwerkkarte", "Network", "Adapter", "Card", "Ethernet", "Gigabit", "Controller", "Interface", "PCI", "Express"]
        brand_clean = self.clean_brand_name(p_name, remove_list)
        
        parts = [brand_clean, speed_short, interface_short, port_short]
        parts_clean = [p for p in parts if p and "N/A" not in p]
        
        short_name = " ".join(parts_clean).strip()
        short_name = re.sub(r'\s+', ' ', short_name)

        return {
            "kWarengruppe": 20,
            "Attribute": {
                "shortNameLang": short_name,
                "low_profile": is_lp,
                "konfiggruppen_typ": "Netzwerkkarte",
                "Seriennummer": 1,
                "upgradeArticle": 1,
                "markup": 0,
                "Hardware": 0
            }
        }
        
    def map_network_adapter_wg21(self, data, html_content=""):
        """Mapping für Warengruppe 21: Netzwerkadapter (USB-Sticks, WLAN-Dongles)"""
        allg = data.get("Allgemein", {})
        p_name = data.get("Produktname", data.get("_Produktname", ""))

        # Erweitere Suche auf alle relevanten Bereiche
        search_areas = ["Technische Daten", "Netzwerk", "Anschlüsse und Schnittstellen", "Leistungen"]

        # 1. Low Profile Check
        lp_str = self.get_val_anywhere(data, ["Technische Daten", "Allgemein"], "Low Profile").lower()
        is_lp = 1 if "ja" in lp_str or "yes" in lp_str or "low profile" in p_name.lower() else 0

        # 2. Geschwindigkeit
        speed_raw = self.get_val_anywhere(data, search_areas, "Übertragungsrate").upper()
        if not speed_raw:
            speed_raw = self.get_val_anywhere(data, search_areas, "Maximale Datenübertragungsrate").upper()

        speed_short = ""
        
        # Gigabit Logik
        if "10 G" in speed_raw or "10000 M" in speed_raw: speed_short = "10GbE"
        elif "2.5 G" in speed_raw or "2500 M" in speed_raw: speed_short = "2.5GbE"
        elif "1 G" in speed_raw or "1000 M" in speed_raw: speed_short = "1GbE"
        
        # Mbit Logik (Deine Beispiele 101744 / 101745)
        elif "300 MBIT" in speed_raw: speed_short = "300 Mbit/s"
        elif "150 MBIT" in speed_raw: speed_short = "150 Mbit/s"
        
        # WiFi Fallback
        elif "WIFI" in speed_raw: speed_short = "WiFi"

        # WiFi Standards (Prio vor Speed)
        if "WIFI 7" in speed_raw or "WIFI 7" in p_name.upper(): speed_short = "WiFi 7"
        elif "WIFI 6E" in speed_raw or "WIFI 6E" in p_name.upper(): speed_short = "WiFi 6E"
        elif "WIFI 6" in speed_raw or "WIFI 6" in p_name.upper(): speed_short = "WiFi 6"

        # 3. Schnittstelle
        interface_raw = self.get_val_anywhere(data, search_areas, "Schnittstelle").upper()
        if not interface_raw:
             interface_raw = self.get_val_anywhere(data, search_areas, "Hostschnittstelle").upper()

        interface_short = "USB" # Default bei Adaptern oft USB
        if "PCI" in interface_raw: interface_short = "PCIe"
        elif "USB" in interface_raw: interface_short = "USB"

        # 4. Port Typ
        port_raw = self.get_val_anywhere(data, search_areas, "Anschlusstyp").upper()
        port_short = ""
        if "SFP" in port_raw: port_short = "SFP+"
        elif "RJ45" in port_raw or "RJ-45" in port_raw: port_short = "RJ45"
        
        # 5. Shortname
        remove_list = ["Netzwerkkarte", "Netzwerkadapter", "Network", "Adapter", "Card", "Ethernet", "Gigabit", "Controller", "Interface", "Dongle", "Stick", "W-Lan", "WLAN"]
        brand_clean = self.clean_brand_name(p_name, remove_list)
        
        parts = [brand_clean, speed_short, interface_short, port_short]
        parts_clean = [p for p in parts if p and "N/A" not in p]
        
        short_name = " ".join(parts_clean).strip()
        short_name = re.sub(r'\s+', ' ', short_name)

        return {
            "kWarengruppe": 21, 
            "Attribute": {
                "shortNameLang": short_name,
                "low_profile": is_lp,
                "konfiggruppen_typ": "Netzwerkadapter",
                "Seriennummer": 1,
                "upgradeArticle": 1,
                "markup": 0,
                "Hardware": 0
            }
        } 
        
    def map_software_wg22(self, data, html_content=""):
        allg = data.get("Allgemein", {})
        det = data.get("Details", {})
        sys = data.get("Systemanforderungen", {})
        p_name = data.get("Produktname", "")

        titel = allg.get("Titel", p_name)
        edition = det.get("Version/Edition", "")
        sprache = self.safe_str(det.get("Sprache", "")).title()
        lizenz = det.get("Lizenzart", "")
        kategorie = self.safe_str(det.get("Kategorie", "")).lower()
        arch = sys.get("Architektur", "")

        kundengruppe = "0" 
        
        is_os = "betriebssystem" in kategorie or "windows" in str(titel).lower() or "server" in str(titel).lower()
        
        if is_os:
            if "Deutsch" in sprache or "German" in sprache or "DE" in str(p_name).upper():
                kundengruppe = "1,2,6"
            elif "Französisch" in sprache or "French" in sprache or "FR" in str(p_name).upper():
                kundengruppe = "7"
            elif "Multi" in sprache:
                kundengruppe = "1,2,6" 

        brand_clean = self.clean_brand_name(p_name, ["Software", "Betriebssystem", "Lizenz", "Key", "Vollversion"])
        
        lang_short = sprache
        if "Deutsch" in sprache: lang_short = "Deutsch"
        elif "Englisch" in sprache: lang_short = "Englisch"
        elif "Multi" in sprache: lang_short = "ML"

        arch_short = ""
        if "64" in str(arch): arch_short = "64-Bit"
        
        parts = [brand_clean, edition, arch_short, lang_short, lizenz]
        parts_clean = [p for p in parts if p and p not in brand_clean] 
        
        short_name = " ".join(parts_clean).strip()
        short_name = re.sub(r'\s+', ' ', short_name)

        return {
            "kWarengruppe": 22,
            "Attribute": {
                "shortNameLang": short_name,
                "kundengruppe": kundengruppe,
                "konfiggruppen_typ": "Software",
                "Seriennummer": 1,
                "upgradeArticle": 1,
                "markup": 0,
                "Hardware": 0
            }
        } 
        
    def map_water_cooling_wg23(self, data, html_content=""):
        allg = data.get("Allgemein", {})
        tech = data.get("Technische Daten", {})
        komp = data.get("Kompatibilität", {})
        feat = data.get("Beleuchtung & Features", {})
        p_name = data.get("Produktname", "")

        rad_str = str(tech.get("Radiatorgröße", ""))
        rad_mm = self.extract_number(rad_str)
        
        aio_slots = "0"
        if rad_mm >= 360: aio_slots = "360" 
        elif rad_mm >= 240: aio_slots = "240" 
        elif rad_mm >= 120: aio_slots = "120"
        
        sockets_str = self.safe_str(komp.get("Sockel", ""))
        sockets_clean = sockets_str.replace("[", "").replace("]", "").replace("'", "")
        
        has_amd = "AM" in sockets_clean.upper() or "FM" in sockets_clean.upper()
        has_intel = "LGA" in sockets_clean.upper() or "1700" in sockets_clean or "1200" in sockets_clean
        
        cpu_kuehler_typ = 0
        if has_amd and has_intel: cpu_kuehler_typ = 3
        elif has_intel: cpu_kuehler_typ = 2
        elif has_amd: cpu_kuehler_typ = 1

        rgb_text = str(feat) + " " + p_name
        has_rgb = 1 if "RGB" in rgb_text else 0
        has_argb = 1 if "ARGB" in rgb_text or "Addressable" in rgb_text else 0
        
        tdp = int(self._extract_value_with_unit(tech.get("TDP-Klasse", ""), "W|Watt"))

        remove_list = ["Wasserkühlung", "Water Cooling", "Liquid", "Cooler", "CPU", "AiO", "System", "Komplett"]
        brand_clean = self.clean_brand_name(p_name, remove_list)
        
        suffix = f"{rad_mm}mm AiO" if rad_mm > 0 else "AiO"
        
        short_name = f"{brand_clean} {suffix}".strip()
        short_name = re.sub(r'\s+', ' ', short_name)

        return {
            "kWarengruppe": 23,
            "Attribute": {
                "shortNameLang": short_name,
                "aioSlots": aio_slots, 
                "cpukuehler_typ": cpu_kuehler_typ,
                "board_cpukuehler_sockel": sockets_clean[:255],
                "tdp": tdp,
                "rgb": has_rgb,
                "argb": has_argb,
                "rgb_anschluss_3pin_argb": has_argb,
                "rgb_anschluss_4pin_rgb": 1 if has_rgb and not has_argb else 0,
                "wakue_slots": 1, 
                "board_wakue_anschluss": 1, 
                "silent": 1 if "silent" in p_name.lower() or "quiet" in p_name.lower() else 0,
                "konfiggruppen_typ": "Wasserkühlung",
                "Seriennummer": 1,
                "upgradeArticle": 1,
                "markup": 0,
                "Hardware": 0
            }
        } 
        
    def map_pc_system_wg24(self, data, html_content=""):
        hw = data.get("Hardware", {})
        sw = data.get("Software", {})
        p_name = data.get("Produktname", "")

        cpu_raw = self.safe_str(hw.get("Prozessor", ""))
        cpu_short = ""
        match_cpu = re.search(r'(i\d-\w+|Ryzen \d \w+)', cpu_raw) 
        if match_cpu: cpu_short = match_cpu.group(1)
        else: 
            if "i9" in cpu_raw: cpu_short = "i9"
            elif "i7" in cpu_raw: cpu_short = "i7"
            elif "i5" in cpu_raw: cpu_short = "i5"
            elif "Ryzen 9" in cpu_raw: cpu_short = "Ryzen 9"
            elif "Ryzen 7" in cpu_raw: cpu_short = "Ryzen 7"
            elif "Ryzen 5" in cpu_raw: cpu_short = "Ryzen 5"

        gpu_raw = self.safe_str(hw.get("Grafikkarte", ""))
        gpu_short = ""
        match_gpu = re.search(r'(RTX\s*\d+\w*|RX\s*\d+\w*|GTX\s*\d+)', gpu_raw, re.IGNORECASE)
        if match_gpu: 
            gpu_short = match_gpu.group(1).upper().replace(" ", "") 
        
        ram_raw = self.safe_str(hw.get("Arbeitsspeicher", ""))
        ram_short = ""
        match_ram = re.search(r'(\d+)\s*GB', ram_raw, re.IGNORECASE)
        if match_ram: ram_short = f"{match_ram.group(1)}GB"

        ssd_raw = self.safe_str(hw.get("Festplatte", ""))
        ssd_short = ""
        match_ssd = re.search(r'(\d+)\s*(TB|GB)', ssd_raw, re.IGNORECASE)
        if match_ssd: ssd_short = f"{match_ssd.group(1)}{match_ssd.group(2)} SSD"

        os_raw = self.safe_str(sw.get("Betriebssystem", ""))
        os_short = ""
        if "11" in os_raw: os_short = "Win11"
        elif "10" in os_raw: os_short = "Win10"
        
        if "Pro" in os_raw: os_short += " Pro"
        elif "Home" in os_raw: os_short += " Home"

        remove_list = ["PC-System", "Gaming", "Desktop", "Computer", "Tower", "System", "Intel", "AMD", "Nvidia", "GeForce"]
        brand_clean = self.clean_brand_name(p_name, remove_list)
        
        parts = [brand_clean, cpu_short, ram_short, ssd_short, gpu_short, os_short]
        parts_clean = [p for p in parts if p]
        
        short_name = " ".join(parts_clean).strip()
        short_name = re.sub(r'\s+', ' ', short_name)

        return {
            "kWarengruppe": 24,
            "Attribute": {
                "shortNameLang": short_name,
                "konfiggruppen_typ": "PC-System",
                "Seriennummer": 1,
                "upgradeArticle": 1,
                "markup": 0,
                "Hardware": 0
            }
        }

    def map_misc_wg33(self, data, html_content=""):
        allg = data.get("Allgemein", {})
        props = data.get("Eigenschaften", {})
        p_name = data.get("Produktname", "")

        dev_type = allg.get("Gerätetyp", "Zubehör")
        feature = props.get("Merkmal", "")
        color = props.get("Farbe", "")
        if color == "N/A": color = ""

        remove_list = ["Sonstiges", "Zubehör", "Gadget", "Verschiedenes"]
        brand_clean = self.clean_brand_name(p_name, remove_list)
        
        parts = [brand_clean, dev_type, feature, color]
        parts_clean = [p for p in parts if p]
        
        short_name = " ".join(parts_clean).strip()
        short_name = re.sub(r'\s+', ' ', short_name)

        return {
            "kWarengruppe": 33,
            "Attribute": {
                "shortNameLang": short_name,
                "konfiggruppen_typ": "Sonstiges",
                "Seriennummer": 0,
                "upgradeArticle": 1,
                "markup": 0,
                "Hardware": 0
            }
        } 
        
    def map_keyboard_wg34(self, data, html_content=""):
        tech = data.get("Technische Daten", {})
        p_name = data.get("Produktname", "")

        layout_raw = self.safe_str(tech.get("Layout", "")).upper()
        layout_short = ""
        if "DE" in layout_raw or "GERMAN" in layout_raw or "QWERTZ" in layout_raw:
            layout_short = "DE"
        elif "US" in layout_raw or "QWERTY" in layout_raw:
            layout_short = "US"
        elif "UK" in layout_raw:
            layout_short = "UK"
        
        switch_raw = self.safe_str(tech.get("Tastenschalter", ""))
        switch_short = ""
        if "MX" in switch_raw or "Mechanical" in switch_raw or "Mechanisch" in switch_raw:
            if "Red" in switch_raw: switch_short = "Mech. Red"
            elif "Blue" in switch_raw: switch_short = "Mech. Blue"
            elif "Brown" in switch_raw: switch_short = "Mech. Brown"
            else: switch_short = "Mechanisch"
        
        conn_raw = self.safe_str(tech.get("Verbindung", "")).lower()
        conn_short = ""
        if "wireless" in conn_raw or "kabellos" in conn_raw or "bluetooth" in conn_raw:
            conn_short = "Wireless"
        elif "usb" in conn_raw or "kabel" in conn_raw:
            conn_short = "USB"

        light_raw = self.safe_str(tech.get("Beleuchtung", "")).upper()
        light_short = "RGB" if "RGB" in light_raw else ""

        remove_list = ["Tastatur", "Keyboard", "Gaming", "Mechanical", "Switch", "Layout"]
        brand_clean = self.clean_brand_name(p_name, remove_list)
        
        parts = [brand_clean, light_short, switch_short, conn_short, layout_short]
        if layout_short: parts.append("Layout") 
        
        parts_clean = [p for p in parts if p]
        
        short_name = " ".join(parts_clean).strip()
        short_name = re.sub(r'\s+', ' ', short_name)

        return {
            "kWarengruppe": 34, 
            "Attribute": {
                "shortNameLang": short_name,
                "konfiggruppen_typ": "Tastatur",
                "Seriennummer": 1,
                "upgradeArticle": 1,
                "markup": 0,
                "Hardware": 0
            }
        }
        
    def map_mouse_wg35(self, data, html_content=""):
        allg = data.get("Allgemein", {})
        tech = data.get("Technische Daten", {})
        p_name = data.get("Produktname", "")

        dpi_raw = self.safe_str(tech.get("Bewegungsauflösung", ""))
        dpi_short = ""
        match_dpi = re.search(r'(\d+)', dpi_raw.replace('.', ''))
        if match_dpi:
            dpi_short = f"{match_dpi.group(1)}dpi"
        
        conn_raw = self.safe_str(tech.get("Anschlusstechnik", "")).lower()
        conn_short = ""
        if "wireless" in conn_raw or "kabellos" in conn_raw or "bluetooth" in conn_raw:
            conn_short = "Wireless"
        elif "usb" in conn_raw or "verkabelt" in conn_raw:
            conn_short = "USB"
            
        color = allg.get("Farbe", "Schwarz")
        if color == "N/A": color = ""

        remove_list = ["Maus", "Mouse", "Gaming", "Optical", "Sensor", "Auflösung"]
        brand_clean = self.clean_brand_name(p_name, remove_list)
        
        parts = [brand_clean, conn_short, dpi_short, "Maus", color]
        parts_clean = [p for p in parts if p]
        
        short_name = " ".join(parts_clean).strip()
        short_name = re.sub(r'\s+', ' ', short_name)

        return {
            "kWarengruppe": 35,
            "Attribute": {
                "shortNameLang": short_name,
                "konfiggruppen_typ": "Maus",
                "Seriennummer": 1,
                "upgradeArticle": 1,
                "markup": 0,
                "Hardware": 0
            }
        } 
        
    def map_headset_wg36(self, data, html_content=""):
        allg = data.get("Allgemein", {})
        tech = data.get("Technische Daten", {})
        p_name = data.get("Produktname", "")

        conn_raw = self.safe_str(tech.get("Anschlusstechnik", "")).lower()
        conn_short = ""
        if "wireless" in conn_raw or "kabellos" in conn_raw or "bluetooth" in conn_raw or "funk" in conn_raw:
            conn_short = "Wireless"
        elif "usb" in conn_raw or "kabel" in conn_raw or "verkabelt" in conn_raw:
            conn_short = "USB" 

        sound_raw = self.safe_str(tech.get("Soundmodus", "")).upper()
        sound_short = ""
        if "7.1" in sound_raw: sound_short = "7.1"
        elif "SURROUND" in sound_raw: sound_short = "Surround"
        
        color = allg.get("Farbe", "Schwarz")
        if color == "N/A": color = ""

        remove_list = ["Headset", "Gaming", "Kopfhörer", "Headphones", "Ear", "Ohrhörer"]
        brand_clean = self.clean_brand_name(p_name, remove_list)
        
        parts = [brand_clean, conn_short, sound_short, "Headset", color]
        parts_clean = [p for p in parts if p]
        
        short_name = " ".join(parts_clean).strip()
        short_name = re.sub(r'\s+', ' ', short_name)

        return {
            "kWarengruppe": 36, 
            "Attribute": {
                "shortNameLang": short_name,
                "konfiggruppen_typ": "Headset",
                "Seriennummer": 1,
                "upgradeArticle": 1,
                "markup": 0,
                "Hardware": 0
            }
        } 
        
    def map_streaming_wg37(self, data, html_content=""):
        allg = data.get("Allgemein", {})
        tech = data.get("Technische Daten", {})
        p_name = data.get("Produktname", "")

        dev_type = allg.get("Gerätetyp", "Streaming Gear")
        
        feature_short = ""
        
        res = self.safe_str(tech.get("Auflösung (Video)", ""))
        if res and res != "N/A":
            if "4K" in res: feature_short = "4K"
            if "60" in res: feature_short += "60"
            elif "1080" in res: feature_short = "1080p"
            
        keys = self.safe_str(tech.get("Anzahl Tasten", ""))
        match_keys = re.search(r'(\d+)', keys)
        if match_keys:
            feature_short = f"{match_keys.group(1)} Tasten"

        conn_raw = self.safe_str(tech.get("Schnittstelle", "")).upper()
        conn_short = ""
        if "PCI" in conn_raw: conn_short = "PCIe"
        elif "USB" in conn_raw: conn_short = "USB"

        remove_list = ["Streaming", "Capture", "Card", "Game", "Controller", "Live"]
        brand_clean = self.clean_brand_name(p_name, remove_list)
        
        parts = [brand_clean, feature_short, conn_short, dev_type]
        parts_clean = [p for p in parts if p and p not in brand_clean]
        
        short_name = " ".join(parts_clean).strip()
        short_name = re.sub(r'\s+', ' ', short_name)

        return {
            "kWarengruppe": 37,
            "Attribute": {
                "shortNameLang": short_name,
                "konfiggruppen_typ": "Streaming",
                "Seriennummer": 1, 
                "upgradeArticle": 1,
                "markup": 0,
                "Hardware": 0
            }
        }  
        
    def map_speakers_wg38(self, data, html_content=""):
        allg = data.get("Allgemein", {})
        tech = data.get("Technische Daten", {})
        conn = data.get("Konnektivität", {})
        p_name = data.get("Produktname", "")

        channels = self.safe_str(tech.get("Kanäle", ""))
        sys_short = ""
        if "5.1" in channels: sys_short = "5.1"
        elif "2.1" in channels: sys_short = "2.1"
        elif "2.0" in channels: sys_short = "2.0"
        elif "Soundbar" in channels or "Soundbar" in p_name: sys_short = "Soundbar"

        power_raw = self.safe_str(tech.get("Gesamtleistung", ""))
        power_short = ""
        match_power = re.search(r'(\d+)', power_raw)
        if match_power:
            power_short = f"{match_power.group(1)}W"

        conn_str = self.safe_str(conn.get("Schnittstellen", ""))
        bt_short = "Bluetooth" if "Bluetooth" in conn_str or "BT" in conn_str else ""
        
        color = allg.get("Farbe", "Schwarz")
        if color == "N/A": color = ""

        remove_list = ["Lautsprecher", "Speaker", "System", "Boxen", "Sound", "Multimedia"]
        brand_clean = self.clean_brand_name(p_name, remove_list)
        
        parts = [brand_clean, sys_short, power_short, bt_short, "Lautsprecher", color]
        parts_clean = [p for p in parts if p]
        
        short_name = " ".join(parts_clean).strip()
        short_name = re.sub(r'\s+', ' ', short_name)

        return {
            "kWarengruppe": 38,
            "Attribute": {
                "shortNameLang": short_name,
                "konfiggruppen_typ": "Lautsprecher",
                "Seriennummer": 1,
                "upgradeArticle": 1,
                "markup": 0,
                "Hardware": 0
            }
        }  
        
    def map_mousepad_wg39(self, data, html_content=""):
        allg = data.get("Allgemein", {})
        tech = data.get("Technische Daten", {})
        feat = data.get("Ausstattung", {})
        p_name = data.get("Produktname", "")

        size_cls = self.safe_str(tech.get("Größenklasse", ""))
        dims = self.safe_str(tech.get("Abmessungen", ""))
        
        size_short = ""
        if size_cls and size_cls != "N/A":
            size_short = size_cls
        elif dims:
            width_match = re.search(r'(\d{3,4})', dims)
            if width_match:
                width = int(width_match.group(1))
                if width >= 800: size_short = "Extended XXL"
                elif width >= 400: size_short = "Large"
                else: size_short = "Medium"

        mat_raw = self.safe_str(tech.get("Material", "")).lower()
        mat_short = "Stoff" 
        if "hard" in mat_raw or "plastik" in mat_raw or "kunststoff" in mat_raw:
            mat_short = "Hard"
        elif "hybrid" in mat_raw:
            mat_short = "Hybrid"

        feat_str = self.safe_str(feat.get("Besonderheiten", ""))
        rgb_short = "RGB" if "RGB" in feat_str or "Beleuchtung" in feat_str else ""

        color = allg.get("Farbe", "Schwarz")
        if color == "N/A": color = ""

        remove_list = ["Mauspad", "Mouse Pad", "Mousepad", "Mat", "Gaming", "Surface", "Unterlage"]
        brand_clean = self.clean_brand_name(p_name, remove_list)
        
        parts = [brand_clean, size_short, rgb_short, mat_short, "Mauspad", color]
        parts_clean = [p for p in parts if p]
        
        short_name = " ".join(parts_clean).strip()
        short_name = re.sub(r'\s+', ' ', short_name)

        return {
            "kWarengruppe": 39, 
            "Attribute": {
                "shortNameLang": short_name,
                "konfiggruppen_typ": "Mauspad",
                "Seriennummer": 0,
                "upgradeArticle": 1,
                "markup": 0,
                "Hardware": 0
            }
        }
        
    def map_desktop_set_wg40(self, data, html_content=""):
        allg = data.get("Allgemein", {})
        tech = data.get("Technische Daten", {})
        p_name = data.get("Produktname", "")

        layout_raw = self.safe_str(tech.get("Layout", "")).upper()
        layout_short = ""
        if "DE" in layout_raw or "GERMAN" in layout_raw or "QWERTZ" in layout_raw:
            layout_short = "DE"
        elif "US" in layout_raw or "QWERTY" in layout_raw:
            layout_short = "US"
        elif "CH" in layout_raw or "SWISS" in layout_raw:
            layout_short = "CH"

        conn_raw = self.safe_str(tech.get("Verbindung", "")).lower()
        conn_short = ""
        if "wireless" in conn_raw or "kabellos" in conn_raw or "bluetooth" in conn_raw or "funk" in conn_raw:
            conn_short = "Wireless"
        elif "usb" in conn_raw or "kabel" in conn_raw:
            conn_short = "USB"

        color = allg.get("Farbe", "Schwarz")
        if color == "N/A": color = ""

        remove_list = ["Set", "Combo", "Desktop", "Maus", "Tastatur", "Keyboard", "Mouse", "Wireless", "Kabellos"]
        brand_clean = self.clean_brand_name(p_name, remove_list)
        
        parts = [brand_clean, "Desktop-Set", conn_short, layout_short, color]
        parts_clean = [p for p in parts if p]
        
        short_name = " ".join(parts_clean).strip()
        short_name = re.sub(r'\s+', ' ', short_name)

        return {
            "kWarengruppe": 40,
            "Attribute": {
                "shortNameLang": short_name,
                "konfiggruppen_typ": "Desktop-Set",
                "Seriennummer": 1,
                "upgradeArticle": 1,
                "markup": 0,
                "Hardware": 0
            }
        } 
        
    def map_service_wg41(self, data, html_content=""):
        allg = data.get("Allgemein", {})
        det = data.get("Details", {})
        p_name = data.get("Produktname", "")

        svc_type = allg.get("Dienstleistungstyp", "Service")
        duration = allg.get("Dauer", "")
        mode = det.get("Art", "")
        
        remove_list = ["Service", "Dienstleistung", "Pack", "Extension", "Erweiterung", "Warranty", "Garantie", "Support"]
        brand_clean = self.clean_brand_name(p_name, remove_list)
        
        parts = [brand_clean, svc_type, duration, mode]
        parts_clean = [p for p in parts if p and p != "N/A"]
        
        short_name = " ".join(parts_clean).strip()
        short_name = re.sub(r'\s+', ' ', short_name)

        return {
            "kWarengruppe": 41,
            "Attribute": {
                "shortNameLang": short_name,
                "konfiggruppen_typ": "Service",
                "Seriennummer": 0,
                "upgradeArticle": 1,
                "markup": 0,
                "Hardware": 0
            }
        }    
        
    def map_usb_stick_wg42(self, data, html_content=""):
        allg = data.get("Allgemein", {})
        p_name = data.get("Produktname", data.get("_Produktname", ""))

        # Wir suchen in diesen Bereichen
        search_areas = ["Technische Daten", "Leistungen", "Schnittstellen", "Speicher"]

        # 1. Kapazität
        cap_raw = self.get_val_anywhere(data, search_areas, "Kapazität").upper()
        cap_short = ""
        match_cap = re.search(r'(\d+)\s*(GB|TB)', cap_raw)
        if match_cap:
            cap_short = f"{match_cap.group(1)}{match_cap.group(2)}"

        # 2. Schnittstelle
        iface_raw = self.get_val_anywhere(data, search_areas, "Schnittstelle").upper()
        if not iface_raw: # Fallback: Geräteschnittstelle oder USB-Version
            iface_raw = self.get_val_anywhere(data, search_areas, "Geräteschnittstelle").upper()
        if not iface_raw:
            iface_raw = self.get_val_anywhere(data, search_areas, "USB-Version").upper()

        iface_short = "USB" 
        if "3.2" in iface_raw: iface_short = "USB 3.2"
        elif "3.1" in iface_raw: iface_short = "USB 3.1"
        elif "3.0" in iface_raw: iface_short = "USB 3.0"
        elif "2.0" in iface_raw: iface_short = "USB 2.0"
        
        if "TYPE-C" in iface_raw or "USB-C" in iface_raw:
            iface_short += " Type-C"
        elif "DUAL" in iface_raw:
            iface_short += " Dual"
        
        # Bluetooth Fallback (dein Beispiel 101113 war ein Bluetooth Stick!)
        if "BLUETOOTH" in iface_raw or "BLUETOOTH" in p_name.upper():
            iface_short = "Bluetooth"
            match_bt = re.search(r'(\d\.\d)', iface_raw)
            if match_bt: iface_short += f" {match_bt.group(1)}"

        color = allg.get("Farbe", "Schwarz")
        if color in ["N/A", ""]: color = ""

        remove_list = ["USB-Stick", "Flash", "Drive", "Speicherstick", "USB", "Stick", "Pen", "Memory", "Bluetooth", "Adapter"]
        brand_clean = self.clean_brand_name(p_name, remove_list)
        
        parts = [brand_clean, cap_short, iface_short, "Stick", color]
        parts_clean = [p for p in parts if p and "N/A" not in p]
        
        short_name = " ".join(parts_clean).strip()
        short_name = re.sub(r'\s+', ' ', short_name)

        return {
            "kWarengruppe": 42, 
            "Attribute": {
                "shortNameLang": short_name,
                "konfiggruppen_typ": "USB-Stick",
                "Seriennummer": 0,
                "upgradeArticle": 1,
                "markup": 0,
                "Hardware": 0
            }
        }                                         
                  
    # ==========================================
    # 🎛️ MAIN DISPATCHER 
    # ==========================================
    def create_json(self, source_file, data, html_content=None):
        filename = os.path.basename(source_file)
        
        # --- ROBUSTNESS CHECK ---
        if not isinstance(data, dict):
            print(f"   ⚠️ FEHLER: Daten für {filename} sind kein Dictionary. Überspringe Mapping.")
            return

        json_str = json.dumps(data, ensure_ascii=False).lower()
        root_keys = [k.lower() for k in data.keys()]
        
        allgemein = data.get("Allgemein", {})
        allgemein_str = json.dumps(allgemein, ensure_ascii=False).lower()
        
        marvin_json = {}
        found_category = False
        cat_debug = ""

        # TRY-CATCH BLOCK GLOBAL FÜR JEDES MAPPING
        try:
            # 1. MAINBOARD
            if "unterstützter ram" in root_keys or ("chipsatz" in allgemein_str and "audio" in root_keys):
                marvin_json = self.map_mainboard(data, html_content)
                found_category = True
                cat_debug = "Mainboard"

            # 2. CPU
            elif "speicher-controller" in root_keys or "prozessor" in root_keys:
                marvin_json = self.map_cpu(data, html_content)
                found_category = True
                cat_debug = "Prozessor"

            # 3. GPU
            elif "systemanforderungen" in root_keys and "grafikprozessor" in allgemein_str:
                marvin_json = self.map_gpu(data, html_content)
                found_category = True
                cat_debug = "Grafikkarte"

            # 4. RAM
            elif "arbeitsspeicher" in root_keys and "grafikprozessor" not in allgemein_str:
                marvin_json = self.map_ram(data, html_content)
                found_category = True
                cat_debug = "RAM"
            
            # 5. GEHÄUSE
            elif "kühlsystem (installiert)" in root_keys or "gehäuse" in allgemein_str or "midi tower" in allgemein_str:
                marvin_json = self.map_case(data, html_content)
                found_category = True
                cat_debug = "Gehäuse"
            
            # 6. NETZTEIL
            elif "stromversorgungsgerät" in root_keys or "netzteil" in allgemein_str:
                marvin_json = self.map_psu(data, html_content)
                found_category = True
                cat_debug = "Netzteil"
                
            # 7. STORAGE
            elif "festplatte" in root_keys or "ssd" in json_str or "hdd" in json_str or "kapazität" in allgemein_str:
                marvin_json = self.map_storage(data, html_content)
                found_category = True
                cat_debug = "Speicher"    
            
            # 8. MONITOR
            elif "bildschirm" in root_keys or "display" in root_keys or "monitor" in allgemein_str:
                marvin_json = self.map_monitor(data, html_content)
                found_category = True
                cat_debug = "Monitor"
            
            # 9. LÜFTER
            elif "lüfter" in filename.lower() or "fan" in filename.lower() or \
                 "gehäuselüfter" in json_str or \
                 "rotationsgeschwindigkeit" in json_str or \
                 "lüfterdurchmesser" in json_str:
                marvin_json = self.map_fan(data, html_content)
                found_category = True
                cat_debug = "Lüfter"
                
            # WG 23 (WASSERKÜHLUNG)
            elif cat_debug == "Wasserkühlung" or "wasserkühlung" in json_str or "aio" in json_str or "liquid cooler" in json_str:
                marvin_json = self.map_water_cooling_wg23(data, html_content)
                found_category = True
                cat_debug = "Wasserkühlung (WG23)"    
            
            # 10. CPU-KÜHLER
            elif "bauhöhe" in json_str or "radiatorgröße" in json_str or "cpu-kühler" in json_str:
                marvin_json = self.map_cpu_cooler(data, html_content)
                found_category = True
                cat_debug = "CPU-Kühler"
                
            # 11. KÜHLER (WG 12)
            elif cat_debug == "Kühler" or ("kühler" in json_str and "cpu-kühler" not in json_str):
                marvin_json = self.map_cooler_wg12(data, html_content)
                found_category = True
                cat_debug = "Kühler (WG12)"   
                
            # WG 14
            elif cat_debug == "Eingabegeräte" or "tastatur" in json_str or "maus" in json_str or "eingabegerät" in json_str:
                marvin_json = self.map_input_devices_wg14(data, html_content)
                found_category = True
                cat_debug = "Eingabegeräte (WG14)"
                
            # WG 15 (KABEL)
            elif (cat_debug == "Kabel" or "kabel" in json_str or "adapter" in json_str or "anschluss a" in json_str) \
                 and "netzwerk" not in json_str and "network" not in json_str and "wlan" not in json_str:
                marvin_json = self.map_cables_wg15(data, html_content)
                found_category = True
                cat_debug = "Kabel (WG15)"        
            
            # WG 16 (SOUND)
            elif cat_debug == "Soundkarte" or "soundkarte" in json_str or "sound card" in json_str:
                marvin_json = self.map_soundcard_wg16(data, html_content)
                found_category = True
                cat_debug = "Soundkarte (WG16)"
                
            # WG 17 (AUDIO)
            elif (cat_debug == "Audio" or "mikrofon" in json_str or "microphone" in json_str) and "webcam" not in json_str:
                marvin_json = self.map_audio_wg17(data, html_content)
                found_category = True
                cat_debug = "Audio (WG17)"    
            
            # WG 18 (WEBCAM)
            elif cat_debug == "Webcam" or "webcam" in json_str or "1080p" in json_str:
                marvin_json = self.map_webcam_wg18(data, html_content)
                found_category = True
                cat_debug = "Webcam (WG18)"
                
            # WG 19 (CHAIR)
            elif cat_debug == "Gamingstuhl" or "gamingstuhl" in json_str or "gaming chair" in json_str or "bürostuhl" in json_str:
                marvin_json = self.map_gaming_chair_wg19(data, html_content)
                found_category = True
                cat_debug = "Gamingstuhl (WG19)"    
            
            # WG 20 (NIC)
            elif cat_debug == "Netzwerkkarte" or "netzwerkkarte" in json_str or "network card" in json_str or "nic" in json_str:
                marvin_json = self.map_network_card_wg20(data, html_content)
                found_category = True
                cat_debug = "Netzwerkkarte (WG20)"
            
            # WG 21 (ADAPTER)
            elif cat_debug == "Netzwerkadapter" or "netzwerkadapter" in json_str or "wlan stick" in json_str:
                marvin_json = self.map_network_adapter_wg21(data, html_content)
                found_category = True
                cat_debug = "Netzwerkadapter (WG21)"
                
            # WG 22 (SW)
            elif cat_debug == "Software" or "software" in json_str or "windows" in json_str or "office" in json_str:
                marvin_json = self.map_software_wg22(data, html_content)
                found_category = True
                cat_debug = "Software (WG22)"
                
            # WG 24 (PC)
            elif cat_debug == "PC-System" or "pc-system" in json_str or "komplett-pc" in json_str:
                marvin_json = self.map_pc_system_wg24(data, html_content)
                found_category = True
                cat_debug = "PC-System (WG24)"  
                
            # WG 33 (MISC)
            elif cat_debug == "Sonstiges" or "sonstiges" in json_str or "zubehör" in json_str:
                marvin_json = self.map_misc_wg33(data, html_content)
                found_category = True
                cat_debug = "Sonstiges (WG33)"        
            
            # WG 34 (KEY)
            elif cat_debug == "Tastatur_WG34":
                marvin_json = self.map_keyboard_wg34(data, html_content)
                found_category = True
                cat_debug = "Tastatur (WG34)"
            
            # WG 35 (MOUSE)
            elif cat_debug == "Maus_WG35":
                marvin_json = self.map_mouse_wg35(data, html_content)
                found_category = True
                cat_debug = "Maus (WG35)"
            
            # WG 36 (HEAD)
            elif cat_debug == "Headset_WG36":
                marvin_json = self.map_headset_wg36(data, html_content)
                found_category = True
                cat_debug = "Headset (WG36)"
            
            # WG 37 (STREAM)
            elif cat_debug == "Streaming" or "streaming" in json_str or "capture card" in json_str or "stream deck" in json_str:
                marvin_json = self.map_streaming_wg37(data, html_content)
                found_category = True
                cat_debug = "Streaming (WG37)"        
            
            # WG 38 (SPEAK)
            elif cat_debug == "Lautsprecher" or "lautsprecher" in json_str or "soundbar" in json_str:
                marvin_json = self.map_speakers_wg38(data, html_content)
                found_category = True
                cat_debug = "Lautsprecher (WG38)"  
                
            # WG 39 (PAD)
            elif cat_debug == "Mauspad_WG39":
                marvin_json = self.map_mousepad_wg39(data, html_content)
                found_category = True
                cat_debug = "Mauspad (WG39)"  
                
            # WG 40 (SET)
            elif cat_debug == "Desktop_Set_WG40":
                marvin_json = self.map_desktop_set_wg40(data, html_content)
                found_category = True
                cat_debug = "Desktop-Set (WG40)"  
                
            # WG 41 (SVC)
            elif cat_debug == "Service" or "garantie" in json_str or "warranty" in json_str or "care pack" in json_str:
                marvin_json = self.map_service_wg41(data, html_content)
                found_category = True
                cat_debug = "Service (WG41)"  
                
            # WG 42 (STICK)
            elif cat_debug == "USB-Stick" or "usb-stick" in json_str or "flash drive" in json_str or "thumb drive" in json_str:
                marvin_json = self.map_usb_stick_wg42(data, html_content)
                found_category = True
                cat_debug = "USB-Stick (WG42)"
            
            else:
                print(f"   ⚠️ SKIPPED Marvin-JSON für {filename}: Keine bekannte Struktur erkannt.")
                return

        except Exception as e:
            # HIER WIRD DER ABSTURZ ABGEFANGEN
            print(f"   🔥 CRITICAL MAPPING ERROR für {filename} ({cat_debug}): {e}")
            return

        # Speichern
        if found_category:
            try:
                output_path = os.path.join(self.output_folder, filename.replace(".json", "_marvin.json"))
                with open(output_path, 'w', encoding='utf-8') as f:
                    json.dump(marvin_json, f, indent=4, ensure_ascii=False)
                
                print(f"   👤 Marvin-JSON erstellt ({cat_debug} | WG {marvin_json.get('kWarengruppe')}): {output_path}")
            except Exception as e:
                print(f"   ❌ Fehler beim Speichern der JSON für {filename}: {e}")