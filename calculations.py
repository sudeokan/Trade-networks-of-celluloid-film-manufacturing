
# 1. Get the top countries

country_counts = (
    df_clean["Country"]
    .value_counts()
    .reset_index()
)
country_counts.columns = ["Country", "Count"]
country_counts = country_counts[country_counts["Count"] > 5]
country_counts.index = country_counts.index + 1

print(country_counts)

# 2. Get the top 10 cities

top_cities = (
    df_clean["City"]
    .value_counts()
    .head(10)
    .reset_index()
)
top_cities.columns = ["City", "Count"]
top_cities.index = top_cities.index + 1

print(top_cities)
