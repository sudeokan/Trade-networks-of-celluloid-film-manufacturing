import re
import unicodedata
import pandas as pd
from tqdm.auto import tqdm
from geopy.geocoders import Nominatim
from geopy.extra.rate_limiter import RateLimiter

# ── spaCy multilingual NER ────────────────────────────────────────────────────
try:
    import spacy
    nlp = spacy.load("xx_ent_wiki_sm")
    USE_NER = True
    print("✅ spaCy multilingual NER loaded")
except Exception as e:
    USE_NER = False
    print(f"⚠️  spaCy not available ({e}) — using regex fallback")

# ── Geocoder ──────────────────────────────────────────────────────────────────
geolocator = Nominatim(user_agent="historical_addressbook_cleaner_v1", timeout=10)
geocode = RateLimiter(geolocator.geocode, min_delay_seconds=1.2, swallow_exceptions=True)

# ── Settings ──────────────────────────────────────────────────────────────────
INPUT_FILE     = "Adressen_B.csv"
OUTPUT_FILE    = "cleaned_addresses_B.csv"
NUM_ENTRIES    = None   # set to None to run all
MIN_IMPORTANCE = 0.5   # raise to reduce false positives, lower to catch more cities

# =============================================================================
# NOISE PATTERNS
# =============================================================================

HTML_NOISE       = re.compile(r'<[^>]+>|&\w+;', re.DOTALL)
ANNOTATION_NOISE = re.compile(r'~~[^~]*~~|\^\([^)]*\)|\$[^$]*\$', re.DOTALL)
NUMBER_ONLY      = re.compile(r'^\s*[\d\s\-,./]+\s*$')
POSTAL_CODE      = re.compile(
    r'\b([A-Z]{1,2}\d{1,2}[A-Z]?\s*\d[A-Z]{2}|\d{4,5}|\d{1,2}e?)\b',
    re.IGNORECASE)

FALSE_POSITIVES = {
    "The","Atlas","Metal","Alloys","Society","Zoological","Metall","Bronze",
    "Farben","Industrie","Werke","Usines","Constructeur","Industries",
    "Fabrik","Fabrique","Syndicat","Fils","Frères","Söhne","Gesellschaft",
    "Association","Corporation","Company","Works","Factory","Products",
    "Chemicals","Chemical","Manufacture","Manufacturing","Etablissements",
    "National","International","General","Generale","Centrale","Central",
    "Ancien","Anciens","Nouvelle","Nouvelles","Succ","Successeur","Agent",
    "Agence","Bureau","Office","Depot","Nord","Sud","Est","West","Ouest",
    "Distributors","European","Imperial","House","Kingsway","Distillery",
    "Mills","Trading","Boulevard","Militaire","Rue","Avenue","Street",
    "Road","Straat","Strasse","Laan","Weg","Quai","Chemin","Place",
    "Aluminium","Laminoirs","Suisses",
    "Bale",  # ambiguous — Croatia vs Basel
}

# =============================================================================
# PARSING
# =============================================================================

SKIP_RE = re.compile(
    r'^\s*(Supplier|Address|Name|Adressen|:---|---+|Nº|\s*$)',
    re.IGNORECASE)

def parse_raw_entries(file_path):
    with open(file_path, encoding="utf-8", errors="ignore") as f:
        raw = f.read()
    entries = []
    current = []
    in_quote = False
    for line in raw.split('\n'):
        line = line.rstrip('\r')
        if line.count('"') % 2 == 1:
            in_quote = not in_quote
        current.append(line)
        if not in_quote:
            joined = '\n'.join(current).strip().strip('"')
            if joined and not SKIP_RE.match(joined):
                entries.append(joined)
            current = []
    return entries

# =============================================================================
# EXTRACTION
# =============================================================================

def clean_text(text):
    text = HTML_NOISE.sub(' ', text)
    text = ANNOTATION_NOISE.sub(' ', text)
    text = re.sub(r'[{}()\[\]]', ' ', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def extract_candidates(raw_entry):
    """
    Extract city candidates from ALL lines.
    We trust the geocoder + MIN_IMPORTANCE to reject false positives
    rather than trying to filter lines by type — that approach was too
    aggressive and caused real cities to be skipped.
    """
    lines = [clean_text(l) for l in raw_entry.split('\n')]
    lines = [l for l in lines if l and not NUMBER_ONLY.match(l)]
    if not lines:
        return []

    candidates = []

    # ── Pass 1: NER on all lines ──────────────────────────────────────────────
    if USE_NER:
        for line in lines:
            doc = nlp(line)
            for ent in doc.ents:
                if ent.label_ not in ("GPE", "LOC"):
                    continue
                hit = ent.text.strip()
                if hit in FALSE_POSITIVES or len(hit) < 2:
                    continue
                candidates.append(hit)
                # Split multi-word hits so city at end is not missed
                # e.g. "Boulevard Militaire Brussel" → also try "Brussel"
                words = hit.split()
                if len(words) > 1:
                    for word in words:
                        if word not in FALSE_POSITIVES and len(word) > 2:
                            candidates.append(word)

    # ── Pass 2: regex on last line only as fallback ───────────────────────────
    if not candidates:
        last_line = lines[-1]
        tokens = re.findall(
            r'\b[A-ZÄÖÜÀÁÂÃÉÈÊËÎÏÔÙÛÜÇŒÆ][a-zA-ZäöüàáâãéèêëîïôùûüçœæßÄÖÜÀÁÂÃÉÈÊËÎÏÔÙÛÜÇŒÆ\-]{2,}\b',
            last_line)
        candidates = [t for t in reversed(tokens) if t not in FALSE_POSITIVES]

    return list(dict.fromkeys(candidates))  # deduplicate, preserve order

# =============================================================================
# GEOCODING
# =============================================================================

SETTLEMENT_TYPES = {
    "city","town","village","municipality","suburb",
    "hamlet","administrative","locality","quarter","borough",
}

LANGUAGES = ["nl", "fr", "de", "en"]

def _query_variants(text):
    variants = []
    cleaned = POSTAL_CODE.sub('', text).strip(' .,')
    variants.append(cleaned)
    if cleaned != text:
        variants.append(text)
    folded = unicodedata.normalize("NFD", cleaned)
    folded = "".join(c for c in folded if unicodedata.category(c) != "Mn")
    if folded != cleaned:
        variants.append(folded)
    stripped = re.sub(
        r'\s+(a/M\.?|s/M\.?|am\s+Main|sur\s+\S+|bei\s+\S+|i\.\s*\S+|in\s+\w+).*$',
        '', cleaned, flags=re.IGNORECASE).strip()
    if stripped != cleaned:
        variants.append(stripped)
    seen = set()
    return [v for v in variants if v and not (v in seen or seen.add(v))]

def geocode_city(candidate):
    """
    Returns (standard_city, country) or None if not a real city.
    Requires both correct addresstype AND importance >= MIN_IMPORTANCE
    to filter out surnames/company words that match tiny obscure places.
    """
    if not candidate or len(candidate) < 2:
        return None
    for query in _query_variants(candidate):
        for lang in LANGUAGES:
            location = geocode(query, language=lang, addressdetails=True)
            if not location:
                continue
            raw         = location.raw
            addresstype = raw.get("addresstype", "")
            importance  = float(raw.get("importance", 0))
            if addresstype in SETTLEMENT_TYPES and importance >= MIN_IMPORTANCE:
                en_loc = geocode(query, language="en", addressdetails=True)
                if en_loc:
                    parts = [p.strip() for p in en_loc.address.split(",")]
                    return parts[0], parts[-1]
                parts = [p.strip() for p in location.address.split(",")]
                return parts[0], parts[-1]
    return None

# =============================================================================
# MAIN PIPELINE — one row per city found per entry
# =============================================================================

entries = parse_raw_entries(INPUT_FILE)
if NUM_ENTRIES:
    entries = entries[:NUM_ENTRIES]
print(f"✅ Parsed {len(entries):,} entries")

records = []
for raw in tqdm(entries, desc="Processing"):
    candidates = extract_candidates(raw)

    found_cities = []
    seen_cities  = set()
    for candidate in candidates:
        result = geocode_city(candidate)
        if result:
            city, country = result
            if city.lower() not in seen_cities:
                seen_cities.add(city.lower())
                found_cities.append((city, country))

    if found_cities:
        for city, country in found_cities:
            records.append({
                "Original_Text": raw,
                "City":          city,
                "Country":       country,
            })
    else:
        records.append({
            "Original_Text": raw,
            "City":          "",
            "Country":       "",
        })

df = pd.DataFrame(records)

resolved_entries = df[df["City"] != ""]["Original_Text"].nunique()
total_city_rows  = len(df[df["City"] != ""])
print(f"\n✅ Entries with at least one city: {resolved_entries:,} / {len(entries):,}")
print(f"📍 Total city rows (one per city):  {total_city_rows:,}")

df.to_csv(OUTPUT_FILE, index=False, encoding="utf-8-sig")
print(f"\n📄 Saved to {OUTPUT_FILE}")
df.head(30)
