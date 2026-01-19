import os
from dotenv import load_dotenv

# .env Datei laden (für API Keys)
load_dotenv()

# --- PFADE ---
INPUT_FOLDER = "input_csv"
INPUT_FILE = "artikel.csv"
OUTPUT_FOLDER = "output_JSON"
ERROR_FOLDER = "output_errors"
LOG_FILE = "marvin_pipeline.log"

IMAGES_FOLDER = "input_images" 

MODEL_NAME = "gpt-4o" # Optionale Modelle wären "gpt-4o", "gpt-4o-mini", "gpt-3.5-turbo"
TEMPERATURE = 0 # Temperatur bestimmt das Kreative level der Antworten ==> Mögliche werte sind (0, 1, 2) wobei 0 sehr deterministisch ist und 2 sehr Kreativ

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