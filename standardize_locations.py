import pandas as pd
import numpy as np
from geopy.geocoders import Nominatim
from geopy.extra.rate_limiter import RateLimiter
import unicodedata
import time
import re

# 1. Cleaner Setup with better Rate Limiting
# Use a unique user_agent and a slightly longer timeout
geolocator = Nominatim(user_agent="historical_research_cleaner_v2", timeout=10)

# Increased min_delay to 1.5s and added error_wait_seconds to prevent the 429 hard-block
geocode = RateLimiter(
    geolocator.geocode, 
    min_delay_seconds=1.5, 
    error_wait_seconds=10.0, 
    max_retries=3
)

geo_cache = {}

def standardize_location(city, country):
    if pd.isna(city) or city.lower() in ['nan', 'none', '']:
        return pd.Series([None, None])
    
    key = f"{city}, {country}"
    if key in geo_cache:
        return pd.Series(geo_cache[key])
    
    try:
        # Crucial: addressdetails=True gives us the hierarchy (city vs suburb)
        location = geocode(key, language="en", addressdetails=True)
        
        if location:
            address = location.raw.get("address", {})
            
            # --- PROBLEM 1 FIX: Neighborhood Fragmentation ---
            # We look for the "Major" container first to group neighborhoods
            city_std = (
                address.get("city") or 
                address.get("town") or 
                address.get("municipality") or 
                address.get("village") or
                city # fallback to original if nothing found
            )
            
            # --- PROBLEM 2 FIX: Bilingual Names ("Bruxelles - Brussel") ---
            # If there's a dash or slash, take the first English-friendly part
            city_std = re.split(r' [-/] ', city_std)[0]
            
            # --- PROBLEM 3 FIX: Administrative Clutter ---
            # Remove "City of", "Greater", and parentheticals like "(Saale)"
            city_std = re.sub(r'(?i)City of |Greater |Grad |Municipality| \(.*\)', '', city_std).strip()
            
            country_std = address.get("country", country)
            
            # --- PROBLEM 4 FIX: Junk Results ---
            # If the geocoder returned a street or "highway" instead of a place, 
            # it often means the city name was actually a street name.
            osm_type = location.raw.get("type")
            if osm_type in ["highway", "attraction", "building"]:
                # This is likely a false positive (like "Post Street" -> "Post")
                result = (city, country) # Keep original, don't "standardize" to junk
            else:
                result = (city_std, country_std)
            
            geo_cache[key] = result
            return pd.Series(result)
            
    except Exception:
        pass
    
    return pd.Series([city, country])

# -----------------------------
# 5. Final manual "Bridge" for stubborn cases
# -----------------------------
def final_polish(df):
    mapping = {
        "Brux": "Brussels",
        "Bruxelles": "Brussels",
        "13Th Arrondissement": "Paris",
        "City Of London": "London",
        "Antwerpen": "Antwerp",
        "Greater London": "London"
    }
    df["City"] = df["City"].replace(mapping)
    
    # Remove one-word junk that usually comes from street names
    junk_words = ["Post", "Justice", "Jardin", "Hans", "Marie", "Francois", "Rue"]
    df = df[~df["City"].isin(junk_words)]
    
    return df

# Apply the logic
combined_df[["City", "Country"]] = combined_df.apply(
    lambda row: standardize_location(row["City"], row["Country"]),
    axis=1
)

df_clean = final_polish(combined_df.dropna(subset=["City", "Country"]).copy())

print(df_clean.head())
