import pandas as pd
import numpy as np
from geopy.geocoders import Nominatim
import unicodedata
import time

# Load dataset
df = pd.read_csv("cleaned_combined.csv")

# Keep relevant columns
df = df[["Street", "City", "Country"]].copy()

# -----------------------------
# 1. Basic cleaning
# -----------------------------
for col in ["Street", "City", "Country"]:
    df[col] = df[col].astype(str).str.strip()

df = df.replace(["", "nan", "None"], np.nan)

# -----------------------------
# 2. Normalize text (remove accents, fix casing)
# -----------------------------
def normalize_text(text):
    if pd.isna(text):
        return text
    
    text = text.strip()
    text = unicodedata.normalize("NFKD", text)
    text = "".join([c for c in text if not unicodedata.combining(c)])
    
    return text.title()

df["City"] = df["City"].apply(normalize_text)
df["Country"] = df["Country"].apply(normalize_text)

# -----------------------------
# 3. Geocoder setup
# -----------------------------
geolocator = Nominatim(user_agent="universal_city_cleaner")

# Cache to avoid repeated API calls
geo_cache = {}

# -----------------------------
# 4. Standardize city + country
# -----------------------------
def standardize_location(city, country):
    if pd.isna(city):
        return pd.Series([None, None])
    
    key = f"{city}, {country}"
    
    if key in geo_cache:
        return pd.Series(geo_cache[key])
    
    try:
        location = geolocator.geocode(key, language="en")
        time.sleep(1)  # avoid rate limiting
        
        if location:
            address = location.raw.get("address", {})
            
            # Extract standardized names
            city_std = (
                address.get("city")
                or address.get("town")
                or address.get("village")
                or city
            )
            
            country_std = address.get("country", country)
            
            result = (city_std, country_std)
            geo_cache[key] = result
            return pd.Series(result)
    
    except:
        pass
    
    return pd.Series([city, country])  # fallback

# Apply standardization
df[["City", "Country"]] = df.apply(
    lambda row: standardize_location(row["City"], row["Country"]),
    axis=1
)

# -----------------------------
# 5. Final clean dataset
# -----------------------------
df_clean = df.dropna(subset=["City", "Country"]).copy()

print(df_clean.head())
