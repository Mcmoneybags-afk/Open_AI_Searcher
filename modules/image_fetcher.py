def find_product_image(product_name, category=None):
    """
    Dummy-Funktion (OFFLINE MODUS).
    Gibt sofort einen Platzhalter zurück, da die externe Bildsuche deaktiviert wurde.
    Dies dient als Platzhalter, bis die interne SQL-Bilddatenbank angebunden ist.
    
    Args:
        product_name (str): Name des Produkts
        category (str): Kategorie (wird aktuell ignoriert, da nur Platzhalter)
    """
    return get_placeholder_image(product_name)

def get_placeholder_image(text):
    """ 
    Generiert eine URL für ein Platzhalterbild mit dem Produktnamen als Text.
    Nutzt den Dienst 'placehold.co'.
    """
    safe_text = str(text).replace(" ", "+").replace("/", "").replace("\\", "")[:25]
    
    return f"https://placehold.co/600x400/eeeeee/999999?text={safe_text}&font=roboto"