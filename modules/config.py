import os
from dotenv import load_dotenv

# .env Datei laden (für API Keys)
load_dotenv()

# --- PFADE ---
INPUT_FOLDER = "input_csv"
# WICHTIG: Hier jetzt den Namen deiner Excel-Datei eintragen!
# (Achte darauf, dass die Datei auch wirklich in dem Ordner 'input_csv' liegt)
INPUT_FILE = "artikel.xlsx" 

OUTPUT_FOLDER = "output_JSON"
ERROR_FOLDER = "output_errors"
LOG_FILE = "marvin_pipeline.log"

IMAGES_FOLDER = "input_images" 

MODEL_NAME = "gpt-4o-mini" 
TEMPERATURE = 0 

# --- API KEYS ---
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
GOOGLE_CX = os.getenv("GOOGLE_CX")

def setup_folders():
    """ Erstellt die benötigten Output-Ordner, falls nicht vorhanden. """
    for folder in [OUTPUT_FOLDER, ERROR_FOLDER, IMAGES_FOLDER]:
        if not os.path.exists(folder):
            os.makedirs(folder)
            print(f"📁 Ordner erstellt: {folder}")