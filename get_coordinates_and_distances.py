import pandas as pd
from geopy.geocoders import Nominatim
from geopy.distance import geodesic
import time

# Initialize geocoder
geolocator = Nominatim(user_agent="distance_dataframe_app")

# Optional: cache to avoid repeated API calls
coord_cache = {}

def get_coordinates(place):
    if place in coord_cache:
        return coord_cache[place]
    
    try:
        location = geolocator.geocode(place)
        time.sleep(1)  # avoid rate limiting
        if location:
            coords = (location.latitude, location.longitude)
            coord_cache[place] = coords
            return coords
    except:
        return None
    
    return None


def get_distances_df(cities, origin):
    # Create DataFrame
    df = pd.DataFrame(cities, columns=["City"])
    
    # Get origin coordinates
    origin_coords = get_coordinates(origin)
    
    # Function to compute distance
    def compute_distance(city):
        city_coords = get_coordinates(city)
        if city_coords and origin_coords:
            return round(geodesic(city_coords, origin_coords).km, 2)
        return None
    
    # Apply distance calculation
    df["Distance_km"] = df["City"].apply(compute_distance)
    
    # Sort by distance (closest first, missing values last)
    df = df.sort_values(by="Distance_km", ascending=True, na_position="last")
    
    # Reset index
    df = df.reset_index(drop=True)
    df.index = df.index + 1  # optional: start index at 1
    
    return df


# 🔹 Example usage with your dataset
top_city_list = df_clean["City"].value_counts().head(10).index.tolist()

df_distances = get_distances_df(top_city_list, "Antwerp")

print(df_distances)
