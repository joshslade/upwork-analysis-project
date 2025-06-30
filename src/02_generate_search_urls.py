import urllib.parse

# --------------------------------------------------------------
# Define the search parameters
# --------------------------------------------------------------

# Step 1: Define the roles you're interested in
roles = [
    "Data Scientist",
]

# Step 2: Core skills crucial to these roles
core_skills = [
    "Data Science",
    "Python"
    "Machine Learning"
]

# Step 3: Specialized skills or sub-fields you excel in
specialized_skills = ["Optimisation", "Predictive Modelling", "Forecasting"]

# Step 4: Technologies and libraries you're comfortable with or wish to work on
# technologies = ["Azure", "TensorFlow", "Keras", "Scikit-Learn", "LangChain"]
technologies = []
# Step 5: Combine all the keywords
keywords = roles + core_skills + specialized_skills + technologies

# Step 6: Keywords you want to avoid in your job search
# excluded_keywords = ["AWS", "Google Cloud", "React", "Angular", "Django", "Tableau"]
excluded_keywords = []

print(keywords)
print(excluded_keywords)

"""
Additional url parameter to consider to narrow your search:
- &payment_verified=1
- &client_hires=1-9
- &client_hires=10-
- &proposals=0-4
- &proposals=5-9
- &location=United%20States
"""


def generate_upwork_urls(keywords, excluded_keywords, payment_verified=True):
    blacklist_part = " OR ".join([f'"{item}"' for item in excluded_keywords])
    base_url = "https://www.upwork.com/nx/jobs/search/?sort=recency&per_page=50"

    if payment_verified:
        base_url += "&payment_verified=1"

    urls = []
    query_parts = []

    for item in keywords:
        temp_query_parts = query_parts + [f'"{item}"']
        temp_query = f"({' OR '.join(temp_query_parts)}) AND NOT ({blacklist_part})"
        temp_url = f"{base_url}&q={urllib.parse.quote(temp_query)}"

        if len(temp_url) > 500:
            query = f"({' OR '.join(query_parts)}) AND NOT ({blacklist_part})"
            urls.append(f"{base_url}&q={urllib.parse.quote(query)}")
            query_parts = [f'"{item}"']
        else:
            query_parts.append(f'"{item}"')

    # Add the remaining queries
    if query_parts:
        query = f"({' OR '.join(query_parts)}) AND NOT ({blacklist_part})"
        urls.append(f"{base_url}&q={urllib.parse.quote(query)}")

    return urls


# Generate URLs
urls = generate_upwork_urls(keywords, excluded_keywords)

# Print the generated URLs
for url in urls:
    print(url)
