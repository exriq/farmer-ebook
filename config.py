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
ANIMALS = ["Cattle (dairy)", "Cattle (beef/zebu)", "Goats", "Sheep", "Pigs (swine)",
           "Rabbits", "Chickens", "Fish"]
# These are registered one animal at a time, each with a tag number or a name.
TAGGED_ANIMALS = ["Cattle (dairy)", "Cattle (beef/zebu)", "Goats", "Sheep", "Pigs (swine)"]
FISH_SYSTEMS = ["Pond", "Cage"]
FISH_BREEDS = ["Nile tilapia", "African catfish", "Common carp", "Other"]
# How often the farmer harvests fish (name shown -> days between harvests)
HARVEST_FREQ = {"Every week": 7, "Every 2 weeks": 14, "Every month": 30,
                "Every 2 months": 60, "Every 3 months": 90,
                "Once at the end of the cycle (about 6 months)": 180}

COAT_COLOURS = ["Black", "White", "Brown", "Red", "Pink", "Grey",
                "Fawn (light yellowish-brown)",
                "Black and white patches (Friesian / pied)",
                "Brown and white patches", "Red and white patches",
                "Roan (white and coloured hairs mixed)", "Brindle (striped)",
                "Dun (dull yellowish-brown)", "Spotted", "Other"]

# The professional name for the class of animal (what it is, by sex and age)
ANIMAL_CLASSES = {
    "Cattle (dairy)": ["Cow (female that has calved)", "Heifer (young female, not yet calved)",
                       "Bull (adult male)", "Steer / ox (castrated male)",
                       "Female calf", "Male calf"],
    "Cattle (beef/zebu)": ["Cow (female that has calved)", "Heifer (young female, not yet calved)",
                           "Bull (adult male)", "Steer / ox (castrated male)",
                           "Female calf", "Male calf"],
    "Goats": ["Doe (adult female)", "Buck (adult male)", "Wether (castrated male)",
              "Female kid", "Male kid"],
    "Sheep": ["Ewe (adult female)", "Ram (adult male)", "Wether (castrated male)",
              "Ewe lamb (young female)", "Ram lamb (young male)"],
    "Pigs (swine)": ["Sow (female that has farrowed)", "Gilt (young female, not yet farrowed)",
                     "Boar (adult male)", "Barrow (castrated male)", "Weaner / grower",
                     "Piglet"],
}

# What the farmer gets from each animal. These become the "Product" in sales reports.
ANIMAL_PRODUCTS = {
    "Cattle (dairy)": ["Milk", "Meat (beef)", "Calves for sale", "Manure",
                       "Hides and skins", "Draught power (ploughing or carting)"],
    "Cattle (beef/zebu)": ["Meat (beef)", "Calves for sale", "Manure", "Hides and skins",
                           "Draught power (ploughing or carting)"],
    "Goats": ["Meat (chevon)", "Milk", "Kids for sale", "Manure", "Skins"],
    "Sheep": ["Meat (mutton)", "Wool", "Lambs for sale", "Manure", "Skins"],
    "Pigs (swine)": ["Pork", "Piglets for sale", "Manure"],
    "Rabbits": ["Meat", "Breeding rabbits for sale", "Manure and urine"],
    "Chickens": ["Eggs", "Meat", "Chicks or pullets for sale", "Manure"],
    "Fish": ["Fresh fish (table size)", "Fingerlings for sale"],
}
LIVE_SALE = "Live animal (sold alive)"

KEEPING_SYSTEMS = {
    "Cattle (dairy)": ["Zero-grazing (kept in a shed)", "Semi-zero grazing", "Free grazing"],
    "Cattle (beef/zebu)": ["Free grazing", "Paddock grazing", "Feedlot"],
    "Goats": ["Free grazing", "Tethered", "Zero-grazing (kept in a shed)"],
    "Sheep": ["Free grazing", "Tethered", "Zero-grazing (kept in a shed)"],
    "Pigs (swine)": ["Housed in a pen", "Free range or tethered"],
    "Rabbits": ["Hutches (cages)", "Floor or colony"],
    "Chickens": ["Free range", "Semi-intensive", "Intensive (deep litter or cages)"],
}
BREED_EXAMPLES = {
    "Cattle (dairy)": "e.g. Friesian, Ayrshire, Jersey", "Cattle (beef/zebu)": "e.g. Boran, Zebu, Sahiwal",
    "Goats": "e.g. Galla, Toggenburg, Boer", "Sheep": "e.g. Dorper, Red Maasai",
    "Pigs (swine)": "e.g. Large White, Landrace, Duroc", "Rabbits": "e.g. New Zealand White",
    "Chickens": "e.g. Kienyeji, Kuroiler, Layers",
}

_HEALTH = ["Vaccinated", "Dewormed", "Tick control", "Treated for illness"]
_END = ["Bought", "Sold", "Died"]
ANIMAL_ACTIVITIES = {
    "Cattle (dairy)": ["Milk produced", "Weighed", "Calved", "AI / service"] + _HEALTH + _END,
    "Cattle (beef/zebu)": ["Weighed", "Calved", "AI / service"] + _HEALTH + _END,
    "Goats": ["Milk produced", "Weighed", "Kidded", "AI / service"] + _HEALTH + _END,
    "Sheep": ["Wool shorn", "Weighed", "Lambed", "AI / service"] + _HEALTH + _END,
    "Pigs (swine)": ["Weighed", "Farrowed", "AI / service"] + _HEALTH + _END,
    "Rabbits": ["Kindled", "Treated for illness"] + _END,
    "Chickens": ["Eggs collected", "Hatched", "Feed given", "Vaccinated",
                 "Treated for illness"] + _END,
    "Fish": ["Stocked fingerlings", "Feed given", "Catch / harvest", "Died"],
}
LIVESTOCK_UNITS = {
    "Milk produced": ["litres"],
    "Eggs collected": ["eggs", "trays"],
    "Wool shorn": ["kg"],
    "Feed given": ["kg"],
    "Stocked fingerlings": ["fingerlings"],
    "Catch / harvest": ["kg", "pieces"],
}
PRODUCTION_ACTIVITIES = ["Milk produced", "Eggs collected", "Wool shorn", "Catch / harvest"]
# The product a production record is sold as (this shows up in the money reports)
PRODUCT_OF_ACTIVITY = {"Milk produced": "Milk", "Eggs collected": "Eggs", "Wool shorn": "Wool",
                       "Catch / harvest": "Fresh fish (table size)"}
BIRTH_ACTIVITIES = ["Calved", "Kidded", "Lambed", "Farrowed", "Kindled", "Hatched"]

# What each activity is called on screen, and what the farmer must fill in.
ACTIVITY_INFO = {
    "Milk produced": ("🥛 Milk produced", "Fill in: the litres SOLD and the litres USED AT HOME. "
                      "If you type the price per litre, the sale is added to Money for you."),
    "Eggs collected": ("🥚 Eggs collected", "Fill in: the eggs SOLD and the eggs USED AT HOME. "
                       "Type the price per egg or tray to add the sale to Money."),
    "Wool shorn": ("🧶 Wool shorn", "Fill in: the kg of wool SOLD and the kg KEPT. "
                   "Type the price per kg to add the sale to Money."),
    "Catch / harvest": ("🎣 Fish harvested", "Fill in: the kg SOLD and the kg USED AT HOME. "
                        "Type the price per kg to add the sale to Money."),
    "Weighed": ("⚖️ Weighed", "Fill in: the weight in kg. The animal's weight on My Farm is updated."),
    "Calved": ("🍼 Calved (gave birth)", "Fill in: how many calves were born alive and how many dead."),
    "Kidded": ("🍼 Kidded (gave birth)", "Fill in: how many kids were born alive and how many dead."),
    "Lambed": ("🍼 Lambed (gave birth)", "Fill in: how many lambs were born alive and how many dead."),
    "Farrowed": ("🍼 Farrowed (gave birth)", "Fill in: how many piglets were born alive and how many dead."),
    "Kindled": ("🍼 Kindled (gave birth)", "Fill in: how many kits were born alive and how many dead."),
    "Hatched": ("🐣 Chicks hatched", "Fill in: how many chicks hatched alive. They are added to your flock."),
    "AI / service": ("🧬 Served or inseminated", "Fill in: the bull, buck or semen used, and the cost if any."),
    "Vaccinated": ("💉 Vaccinated", "Fill in: how many animals, the vaccine name, and the cost if any."),
    "Dewormed": ("💊 Dewormed", "Fill in: how many animals, the drug name, and the cost if any."),
    "Tick control": ("🪳 Tick control (dipping or spraying)", "Fill in: how many animals, the product used, and the cost if any."),
    "Treated for illness": ("🩺 Treated for illness", "Fill in: how many animals, what was wrong, the drug used and the cost."),
    "Bought": ("🛒 Bought animals", "Fill in: how many you bought and the total you paid. The animals are added to your count."),
    "Sold": ("💰 Sold animals alive", "Fill in: how many you sold and the total money you received. "
             "The sale is added to Money for you."),
    "Died": ("💀 Died", "Fill in: how many died and the cause. They are taken off your count."),
    "Feed given": ("🍽 Feed given", "Fill in: the kg of feed given and what it cost."),
    "Stocked fingerlings": ("🐟 Stocked fingerlings", "Fill in: how many fingerlings you put in and what they cost. "
                            "The harvest countdown starts again from this date."),
}
ACTIVITY_FIELDS = {
    "Milk produced": ["split"], "Eggs collected": ["split"], "Wool shorn": ["split"],
    "Catch / harvest": ["split", "fish_count"], "Weighed": ["weight"],
    "Calved": ["born"], "Kidded": ["born"], "Lambed": ["born"], "Farrowed": ["born"],
    "Kindled": ["born"], "Hatched": ["born"],
    "AI / service": ["service", "cost"],
    "Vaccinated": ["count", "medicine", "cost"], "Dewormed": ["count", "medicine", "cost"],
    "Tick control": ["count", "medicine", "cost"],
    "Treated for illness": ["count", "illness", "medicine", "cost"],
    "Bought": ["count", "cost"], "Sold": ["count", "price"], "Died": ["count", "cause"],
    "Feed given": ["feed", "cost"], "Stocked fingerlings": ["count", "cost"],
}
DEATH_CAUSES = ["Disease", "Old age", "Injury or accident", "Predator or theft",
                "Drought or lack of feed", "Problem at birth", "Poisoning", "Not known"]
# Where the cost of an activity goes in the Money page
LIVESTOCK_COST_CATEGORY = {
    "Vaccinated": "Drugs and vet", "Dewormed": "Drugs and vet", "Tick control": "Drugs and vet",
    "Treated for illness": "Drugs and vet", "AI / service": "Drugs and vet",
    "Bought": "Animals bought", "Feed given": "Feed", "Stocked fingerlings": "Fingerlings",
}

# ---------- MORE ABOUT CROPS ----------
CROP_PRODUCTS = {
    "Cereals": ["Dry grain", "Green or fresh cobs", "Stalks and stover (animal feed)"],
    "Legumes": ["Dry grain (shelled)", "Fresh green pods", "Haulms (animal feed)"],
    "Roots and tubers": ["Fresh roots or tubers", "Dried chips or flour", "Planting cuttings or vines"],
    "Leafy vegetables": ["Fresh leaves", "Seed"],
    "Other vegetables": ["Fresh produce", "Seed"],
    "Fruits": ["Fresh fruit", "Seedlings"],
    "Cash and oil crops": ["Raw harvest (seed cotton, cane, seed)", "Processed (oil, flour)"],
}
PLANTING_METHODS = ["Seed sown directly", "Seedlings transplanted", "Cuttings or vines",
                    "Suckers or splits", "Tubers or bulbs"]
GROWING_SYSTEMS = ["Rain-fed", "Irrigated", "Greenhouse or shade net"]
SEED_SOURCES = ["Certified seed from an agrovet", "Seed saved from my last harvest",
                "From a neighbour or group", "Other"]
LAND_PREP_METHODS = ["Hand hoe (jembe)", "Ox plough", "Tractor", "Minimum tillage (no ploughing)"]
FERTILIZER_TYPES = ["DAP", "CAN", "Urea", "NPK", "Farmyard manure or compost", "Lime", "Other"]
SPRAY_TARGETS = ["Insect pests", "Fungal disease", "Weeds", "Other"]
WEEDING_METHODS = ["Hand hoe (jembe)", "Herbicide", "Cultivator"]
CROP_ACTIVITY_INFO = {
    "Land preparation": ("🚜 Land preparation", "Fill in: the acres prepared, how it was done, and the cost."),
    "Planting": ("🌱 Planting", "Fill in: the acres planted, the seed used, and the seed cost."),
    "Fertilizer applied": ("🧪 Fertilizer applied", "Fill in: which fertilizer, how much, and the cost."),
    "Spraying": ("💦 Spraying", "Fill in: what you sprayed, against what, how much, and the cost."),
    "Weeding": ("🌿 Weeding", "Fill in: the acres weeded, how, and the cost."),
    "Harvest": ("🧺 Harvest", "Fill in: which product, the amount SOLD and the amount USED AT HOME. "
                "Type the price to add the sale to Money for you."),
}
# Where the cost of a crop activity goes in the Money page
CROP_COST_CATEGORY = {"Land preparation": "Other expense", "Planting": "Seed",
                      "Fertilizer applied": "Fertilizer", "Spraying": "Chemicals",
                      "Weeding": "Labour"}
CROP_SALE_UNITS = ["kg", "90-kg bag", "50-kg bag", "tonnes", "pieces", "bunches"]

_PRODUCT_CATEGORY = {"Milk": "Milk sales", "Eggs": "Poultry / egg sales",
                     "Fresh fish (table size)": "Fish sales", "Fingerlings for sale": "Fish sales"}


def income_category(enterprise, product):
    """The money category a sale falls under, worked out from what was sold."""
    if product in _PRODUCT_CATEGORY:
        return _PRODUCT_CATEGORY[product]
    if enterprise == "Cotton":
        return "Cotton sales"
    if enterprise in ANIMALS:
        return "Livestock sales"
    if enterprise in ALL_CROPS:
        return "Crop sales"
    return "Other income"


def units_for(product):
    """Sensible units to sell a product in."""
    p = (product or "").lower()
    if "milk" in p:
        return ["litres"]
    if "egg" in p:
        return ["eggs", "trays"]
    if "fingerling" in p:
        return ["fingerlings"]
    if "live animal" in p or "for sale" in p or "breeding" in p:
        return ["animals"]
    if "draught" in p:
        return ["days"]
    if "manure" in p:
        return ["kg", "bags", "wheelbarrows"]
    if "hide" in p or "skin" in p:
        return ["pieces"]
    if any(w in p for w in ("meat", "pork", "wool", "fish")):
        return ["kg"]
    return CROP_SALE_UNITS

# ---------- MONEY, INPUTS, LABOUR ----------
INCOME_CATEGORIES = ["Crop sales", "Cotton sales", "Milk sales", "Livestock sales",
                     "Poultry / egg sales", "Fish sales", "Other income"]
EXPENSE_CATEGORIES = ["Seed", "Fertilizer", "Chemicals", "Feed", "Drugs and vet",
                      "Fingerlings", "Animals bought", "Labour", "Transport", "Land rent",
                      "Other expense"]
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
