# Trade-networks-of-celluloid-film-manufacturing

This project contains simple Python scripts used for analysing location data and calculating distances for Gevaert’s supplier analysis with the clean preprocessed dataset.

## Installation

-pandas
-geopy
-numpy

## Usage

python preprocessing_A.py and preprocessing_B.py
- Extracts city names from raw, unstructured address text
- Filters out non-geographic noise and business terms
- Standardizes results into a clean City/Country format

python standardize_locations.py
- Combines datasets and makes city/country names consistent
- Fixes spelling, accents, and different language versions
- Groups local districts and neighborhoods into their parent cities

python get_coordinates_and_distances.py
- Converts city names into geographic coordinates
- Calculates distance from a given city

python get_top_cities_and_countries.py
- Counts and ranks the most frequent cities and countries in the dataset

prompts
- example of prompts that were used in generative AI platforms for preprocessing part of the data

Adressen_A.csv and Adressen_B.csv
- raw datasets

cleaned_addresses_A.csv and cleaned_addresses_B.csv
- preprocessed datasets

cleaned_combined.csv
- manually preprocessed dataset used for the GIS geocoding, spatial analysis, and density-based clustering
