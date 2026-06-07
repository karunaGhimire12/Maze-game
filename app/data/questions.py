# data/questions.py
# Question pool for junction checkpoints

QUESTIONS = [
    # --- Easy Math ---
    {"q": "5 + 4 = ?",           "a": "9",   "opts": ["7","8","9","10"],  "diff": "easy"},
    {"q": "12 - 7 = ?",          "a": "5",   "opts": ["3","4","5","6"],   "diff": "easy"},
    {"q": "3 × 6 = ?",           "a": "18",  "opts": ["15","16","18","21"],"diff": "easy"},
    {"q": "20 ÷ 4 = ?",          "a": "5",   "opts": ["4","5","6","8"],   "diff": "easy"},
    {"q": "8 + 13 = ?",          "a": "21",  "opts": ["19","20","21","22"],"diff": "easy"},
    {"q": "7 × 7 = ?",           "a": "49",  "opts": ["42","47","49","56"],"diff": "easy"},
    {"q": "36 ÷ 6 = ?",          "a": "6",   "opts": ["5","6","7","8"],   "diff": "easy"},
    {"q": "15 - 8 = ?",          "a": "7",   "opts": ["5","6","7","9"],   "diff": "easy"},
    {"q": "9 + 6 = ?",           "a": "15",  "opts": ["13","14","15","16"],"diff": "easy"},
    {"q": "4 × 8 = ?",           "a": "32",  "opts": ["28","30","32","36"],"diff": "easy"},

    # --- Medium Math ---
    {"q": "√64 = ?",             "a": "8",   "opts": ["6","7","8","9"],   "diff": "medium"},
    {"q": "3² + 4² = ?",         "a": "25",  "opts": ["20","23","25","30"],"diff": "medium"},
    {"q": "15% of 200 = ?",      "a": "30",  "opts": ["20","25","30","35"],"diff": "medium"},
    {"q": "2³ × 3 = ?",          "a": "24",  "opts": ["16","20","24","32"],"diff": "medium"},
    {"q": "56 ÷ 8 + 5 = ?",      "a": "12",  "opts": ["9","11","12","14"], "diff": "medium"},
    {"q": "5! ÷ 20 = ?",         "a": "6",   "opts": ["4","5","6","8"],   "diff": "medium"},
    {"q": "Prime after 13?",      "a": "17",  "opts": ["15","16","17","19"],"diff": "medium"},
    {"q": "LCM of 4 and 6?",     "a": "12",  "opts": ["8","10","12","24"], "diff": "medium"},
    {"q": "25% of 80 = ?",       "a": "20",  "opts": ["15","18","20","25"],"diff": "medium"},
    {"q": "(-3)² = ?",           "a": "9",   "opts": ["-9","-6","6","9"],  "diff": "medium"},

    # --- Hard Math ---
    {"q": "log₂(32) = ?",        "a": "5",   "opts": ["4","5","6","8"],   "diff": "hard"},
    {"q": "sin(90°) = ?",        "a": "1",   "opts": ["0","0.5","1","√2"],"diff": "hard"},
    {"q": "∫2x dx = ?",          "a": "x²+C","opts": ["2x+C","x+C","x²+C","2x²+C"],"diff":"hard"},
    {"q": "Fib: 8,13,21,__ = ?", "a": "34",  "opts": ["29","30","34","42"],"diff": "hard"},
    {"q": "2^10 = ?",            "a": "1024","opts": ["512","1000","1024","2048"],"diff":"hard"},

    # --- General Knowledge ---
    {"q": "Capital of France?",        "a": "Paris",   "opts": ["Lyon","Paris","Rome","Berlin"],   "diff": "easy"},
    {"q": "Largest planet?",           "a": "Jupiter",  "opts": ["Saturn","Jupiter","Neptune","Uranus"],"diff":"easy"},
    {"q": "H₂O is what?",             "a": "Water",   "opts": ["Oxygen","Hydrogen","Water","Salt"], "diff": "easy"},
    {"q": "How many continents?",      "a": "7",       "opts": ["5","6","7","8"],                   "diff": "easy"},
    {"q": "Speed of light (km/s)?",    "a": "300,000", "opts": ["30,000","300,000","3,000,000","30M"],"diff":"medium"},
    {"q": "Smallest prime number?",    "a": "2",       "opts": ["0","1","2","3"],                   "diff": "easy"},
    {"q": "Chemical symbol for Gold?", "a": "Au",      "opts": ["Ag","Au","Fe","Go"],               "diff": "medium"},
    {"q": "Inventor of telephone?",    "a": "Bell",    "opts": ["Edison","Tesla","Bell","Morse"],    "diff": "medium"},
    {"q": "Boiling point of water °C?","a": "100",     "opts": ["90","95","100","110"],             "diff": "easy"},
    {"q": "DNA stands for?",           "a": "Deoxyribonucleic Acid","opts":["Deoxyribonucleic Acid","Digital Nucleic Acid","Dynamic Nucleic Array","Dense Nucleic Acid"],"diff":"medium"},
    {"q": "Largest ocean?",            "a": "Pacific", "opts": ["Atlantic","Pacific","Indian","Arctic"],"diff":"easy"},
    {"q": "Year WW2 ended?",           "a": "1945",    "opts": ["1943","1944","1945","1946"],        "diff": "medium"},
    {"q": "Shakespeare's era?",        "a": "Renaissance","opts":["Medieval","Renaissance","Baroque","Enlightenment"],"diff":"hard"},
    {"q": "First element (periodic table)?","a":"Hydrogen","opts":["Helium","Lithium","Hydrogen","Carbon"],"diff":"easy"},
    {"q": "Mount Everest continent?",  "a": "Asia",    "opts": ["Africa","Asia","Europe","South America"],"diff":"easy"},
]