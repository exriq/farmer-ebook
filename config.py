"""Settings, lists and small helpers used by every part of UkulimaKonect.
Edit the lists below to change what farmers and coordinators can choose."""
import re
from datetime import timedelta
 
APP_NAME = "UkulimaKonect"
 
# ---------- PEOPLE AND PLACES ----------
SUB_COUNTIES = [
    "Homa Bay Town", "Kabondo Kasipul", "Karachuonyo", "Kasipul",
    "Ndhiwa", "Rangwe", "Suba North", "Suba South",
]
GENDERS = ["Female", "Male", "Prefer not to say"]
FARMING_TYPES = ["Crops", "Livestock", "Mixed"]
FARMING_TYPE_HELP = {
    "Crops": "I grow crops only",
    "Livestock": "I keep animals, birds or fish only",
    "Mixed": "I grow crops and keep animals, birds or fish",
}
ROLES = ["farmer", "coordinator", "admin"]
 
# ---------- LAND ----------
TENURES = [
    "Owned (with title deed)",
    "Owned (no title deed yet)",
    "Community trust land",
    "Leased / rented in",
    "Family / borrowed land",
    "Other",
]
# Used to estimate the most a farm could produce (multipliers of the
# reference yield). These are simple estimates, not measurements.
FERTILITY = {"Low": 0.70, "Medium": 0.85, "High": 1.00}
RAINFALL = {"Poor / unreliable": 0.70, "Fair": 0.85, "Good / reliable": 1.00}
 
 
def scale_for(active_acres):
    """Farm scale worked out from land in active use. Farmers never choose it."""
    acres = float(active_acres or 0)
    if acres <= 0:
        return "Not set"
    if acres < 5:
        return "Small scale"
    if acres < 10:
        return "Semi-large scale"
    return "Large scale"
 
 
# ---------- CROPS ----------
CROP_GROUPS = {
    "Cereals": ["Maize", "Sorghum", "Finger millet", "Bulrush millet", "Rice", "Other cereal"],
    "Legumes": ["Beans", "Groundnuts", "Green grams", "Cowpeas", "Soya beans",
                "Pigeon peas", "Other legume"],
    "Roots and tubers": ["Cassava", "Sweet potato", "Irish potato", "Arrowroots",
                         "Other root or tuber"],
    "Leafy vegetables": ["Kale (sukuma wiki)", "Spinach", "Amaranth (terere)",
                         "African nightshade (managu)", "Spider plant (saget)",
                         "Cowpea leaves (kunde)", "Cabbage", "Other leafy vegetable"],
    "Other vegetables": ["Tomato", "Onion", "Capsicum", "Okra", "Pumpkin", "Eggplant",
                         "Other vegetable"],
    "Fruits": ["Mango", "Banana", "Pawpaw", "Watermelon", "Orange", "Avocado",
               "Passion fruit", "Other fruit"],
    "Cash and oil crops": ["Cotton", "Sunflower", "Sesame (simsim)", "Sugarcane",
                           "Other cash crop"],
}
ALL_CROPS = [c for group in CROP_GROUPS.values() for c in group]
 
# STARTING ESTIMATES ONLY: most a good farm could harvest per acre in one
# season (kg). Replace with figures from the county agriculture office using
# the Admin: Yield Reference page.
CROP_REFERENCE_YIELD = {
    "Maize": 1800, "Sorghum": 1200, "Finger millet": 900, "Bulrush millet": 800,
    "Rice": 2400, "Beans": 800, "Groundnuts": 900, "Green grams": 600,
    "Cowpeas": 600, "Soya beans": 900, "Pigeon peas": 700, "Cassava": 8000,
    "Sweet potato": 8000, "Irish potato": 8000, "Kale (sukuma wiki)": 8000,
    "Spinach": 6000, "Amaranth (terere)": 5000, "African nightshade (managu)": 4000,
    "Spider plant (saget)": 3000, "Cowpea leaves (kunde)": 3000, "Cabbage": 12000,
    "Tomato": 12000, "Onion": 6000, "Capsicum": 5000, "Okra": 3000,
    "Pumpkin": 6000, "Eggplant": 6000, "Watermelon": 8000, "Cotton": 700,
    "Sunflower": 800, "Sesame (simsim)": 400,
}
 
# Yearly production a healthy animal could give (starting estimates).
ANIMAL_POTENTIAL_PER_YEAR = {
    ("Cattle (dairy)", "Milk produced"): ("litres", 3000),
    ("Chickens", "Eggs collected"): ("eggs", 250),
}
 
UNIT_TO_KG = {"kg": 1, "tonnes": 1000, "90-kg bag": 90, "50-kg bag": 50}
 
CROP_ACTIVITIES = {
    "Land preparation": ["acres"],
    "Planting": ["acres"],
    "Fertilizer applied": ["kg", "50-kg bag"],
    "Spraying": ["litres", "acres"],
    "Weeding": ["acres"],
    "Harvest": list(UNIT_TO_KG),
}
 
# ---------- ANIMALS ----------
ANIMALS = ["Cattle (dairy)", "Cattle (beef/zebu)", "Goats", "Sheep", "Chickens", "Fish"]
FISH_SYSTEMS = ["Pond", "Cage"]
FISH_BREEDS = ["Nile tilapia", "African catfish", "Common carp", "Other"]
 
HERD_EVENTS = ["Born", "Died", "Bought", "Sold", "Vaccinated", "Dewormed",
               "Tick control", "Treated for illness", "AI / service"]
ANIMAL_ACTIVITIES = {
    "Cattle (dairy)": HERD_EVENTS + ["Calved", "Milk produced"],
    "Cattle (beef/zebu)": HERD_EVENTS + ["Calved"],
    "Goats": HERD_EVENTS + ["Kidded", "Milk produced"],
    "Sheep": HERD_EVENTS + ["Lambed"],
    "Chickens": ["Bought", "Hatched", "Died", "Sold", "Vaccinated",
                 "Treated for illness", "Eggs collected"],
    "Fish": ["Stocked fingerlings", "Feed given", "Died", "Sold",
             "Catch / harvest"],
}
LIVESTOCK_UNITS = {
    "Milk produced": ["litres"],
    "Eggs collected": ["eggs", "trays"],
    "Feed given": ["kg"],
    "Stocked fingerlings": ["fingerlings"],
    "Catch / harvest": ["kg", "pieces"],
}
PRODUCTION_ACTIVITIES = ["Milk produced", "Eggs collected", "Catch / harvest"]
 
# ---------- MONEY, INPUTS, LABOUR ----------
INCOME_CATEGORIES = ["Crop sales", "Cotton sales", "Milk sales", "Livestock sales",
                     "Poultry / egg sales", "Fish sales", "Other income"]
EXPENSE_CATEGORIES = ["Seed", "Fertilizer", "Chemicals", "Feed", "Drugs and vet",
                      "Fingerlings", "Labour", "Transport", "Land rent", "Other expense"]
INPUT_CATEGORIES = ["Seed", "Fertilizer", "Pesticide / herbicide", "Animal feed",
                    "Veterinary drugs", "Fingerlings", "Tools", "Fuel", "Other"]
INPUT_UNITS = ["kg", "50-kg bag", "litres", "packets", "pieces", "doses"]
WORKER_TYPES = ["Family", "Hired"]
LABOUR_ACTIVITIES = ["Land preparation", "Planting", "Weeding", "Spraying", "Harvesting",
                     "Animal care", "Milking", "Fish pond work", "Other"]
 
# ---------- MARKETS (filled in by coordinators) ----------
LIVESTOCK_PRODUCTS = ["Milk", "Eggs", "Tilapia", "Catfish", "Cattle (live)",
                      "Goat (live)", "Sheep (live)", "Chicken (live)"]
PRODUCTS = ALL_CROPS + LIVESTOCK_PRODUCTS
PRICE_UNITS = ["kg", "90-kg bag", "50-kg bag", "litre", "tray (30 eggs)", "piece",
               "bunch", "head", "tonne"]
DEMAND_LEVELS = ["Low", "Medium", "High"]
DEMAND_SCORE = {"Low": 1, "Medium": 2, "High": 3}
INPUT_ITEMS = [
    "DAP fertilizer", "CAN fertilizer", "Urea", "NPK 17:17:17",
    "Hybrid maize seed (2 kg)", "Bean seed", "Sorghum seed", "Groundnut seed",
    "Pesticide (general)", "Herbicide", "Dairy meal", "Layers mash", "Fish feed",
    "Dewormer", "Acaricide (tick spray)", "Day-old chicks", "Tilapia fingerlings",
]
OPPORTUNITY_TYPES = ["Government", "NGO / development partner", "Private sector / other"]
ALL_SUB_COUNTIES = "All sub-counties"
 
 
# ---------- DATES: SEASONS AND REPORTING PERIODS ----------
def season_label(d):
    """Long rains = March to August. Short rains = September to February.
    Labels sort in date order. Change the months here if your area differs."""
    if 3 <= d.month <= 8:
        return f"{d.year}-A Long rains (Mar-Aug)"
    start_year = d.year if d.month >= 9 else d.year - 1
    return f"{start_year}-B Short rains (Sep-Feb)"
 
 
def period_label(d, period):
    """Return a label for the reporting period that d falls in.
    Labels sort in date order."""
    if period == "Weekly":
        return "Week of " + (d - timedelta(days=d.weekday())).isoformat()
    if period == "Monthly":
        return d.strftime("%Y-%m")
    if period == "Quarterly":
        return f"{d.year}-Q{(d.month - 1) // 3 + 1}"
    if period == "Seasonal":
        return season_label(d)
    return str(d.year)
 
 
PERIODS = ["Weekly", "Monthly", "Quarterly", "Seasonal", "Annual"]
 
 
# ---------- CHECKING WHAT PEOPLE TYPE ----------
def normalize_phone(raw):
    """Return a phone like 0712345678, or None if it is not a Kenyan mobile."""
    p = re.sub(r"[\s\-()]", "", raw or "")
    if p.startswith("+254"):
        p = "0" + p[4:]
    elif p.startswith("254"):
        p = "0" + p[3:]
    return p if re.fullmatch(r"0[17]\d{8}", p) else None
 
 
def parse_coordinate(text, low, high, label):
    """Return (number, error). An empty box is fine: (None, None)."""
    text = (text or "").strip()
    if not text:
        return None, None
    try:
        value = float(text)
    except ValueError:
        return None, f"{label} must be a number, for example -0.5273"
    if not low <= value <= high:
        return None, f"{label} does not look like a place in Kenya."
    return value, None
 
 
LAT_RANGE = (-4.8, 5.2)
LON_RANGE = (33.8, 42.0)
