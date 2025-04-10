import os
import requests
import time
from dotenv import load_dotenv
from supabase import create_client, Client

# --- Configuration ---
load_dotenv()  # Load environment variables from .env file

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_SERVICE_KEY = os.environ.get("SUPABASE_SERVICE_KEY") # Use SERVICE KEY for admin tasks

# TheMealDB API endpoint for searching by first letter
API_BASE_URL = "https://www.themealdb.com/api/json/v1/1/search.php?f="

# Delay between API calls (in seconds) to avoid rate limiting
API_DELAY = 1 
# --------------------

def format_recipe_data(api_recipe):
    """Formats data from TheMealDB API to match the expected database schema."""
    
    ingredients = []
    for i in range(1, 21):  # Check strIngredient1 to strIngredient20
        ingredient = api_recipe.get(f'strIngredient{i}')
        measure = api_recipe.get(f'strMeasure{i}')
        if ingredient and ingredient.strip():  # Check if ingredient is not null/empty
            ingredient_str = f"{measure.strip()} {ingredient.strip()}" if measure and measure.strip() else ingredient.strip()
            ingredients.append(ingredient_str)
            
    # Map API fields to your database columns (adjust keys as needed)
    db_recipe = {
        'name': api_recipe.get('strMeal'),
        'category': api_recipe.get('strCategory'),
        'area': api_recipe.get('strArea'),
        'instructions': api_recipe.get('strInstructions'),
        'image_url': api_recipe.get('strMealThumb'), # Assuming 'image_url' maps to 'strMealThumb'
        'tags': api_recipe.get('strTags'), 
        'youtube_url': api_recipe.get('strYoutube'),
        'source_url': api_recipe.get('strSource'),
        'ingredients': ingredients, # Assumes DB 'ingredients' column is text[] (array)
        # 'id': api_recipe.get('idMeal') # Optional: Store API's ID
    }
    return db_recipe

def main():
    if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
        print("Error: SUPABASE_URL and SUPABASE_SERVICE_KEY environment variables are required.")
        return

    try:
        supabase: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
        print("Supabase client initialized.")
    except Exception as e:
        print(f"Error initializing Supabase client: {e}")
        return

    total_added = 0
    total_skipped = 0
    total_errors = 0
    
    # Iterate through letters 'a' to 'z'
    for letter in "abcdefghijklmnopqrstuvwxyz":
        print(f"\n--- Fetching recipes starting with '{letter}' ---")
        api_url = f"{API_BASE_URL}{letter}"
        
        try:
            response = requests.get(api_url)
            response.raise_for_status()  
            data = response.json()
            recipes = data.get('meals')

            if not recipes:
                print(f"No recipes found for letter '{letter}'.")
                continue

            print(f"Found {len(recipes)} recipes for letter '{letter}'. Processing...")

            for api_recipe in recipes:
                recipe_name = api_recipe.get('strMeal')
                if not recipe_name:
                    print("Skipping recipe with no name.")
                    continue

                try:
                    # 1. Check if recipe already exists (by name)
                    existing_check = supabase.table('recipes').select('id').eq('name', recipe_name).maybe_single().execute()
                    
                    if existing_check.data:
                        # print(f"Recipe '{recipe_name}' already exists. Skipping.") # Uncomment for more detail
                        total_skipped += 1
                        continue

                    # 2. Format data
                    db_data = format_recipe_data(api_recipe)
                    if not db_data.get('name'):
                         print(f"Skipping due to missing name after formatting. Original data ID: {api_recipe.get('idMeal')}")
                         continue

                    # 3. Insert into Supabase
                    # print(f"Inserting recipe: '{db_data['name']}'") # Uncomment for more detail
                    supabase.table('recipes').insert(db_data).execute()
                    total_added += 1

                except Exception as db_err:
                    print(f"Error processing/inserting recipe '{recipe_name}': {db_err}")
                    total_errors += 1

            # Add delay
            print(f"Waiting {API_DELAY} second(s) before next letter...")
            time.sleep(API_DELAY)

        except requests.exceptions.RequestException as req_err:
            print(f"Error fetching data for letter '{letter}': {req_err}")
            total_errors += 1
        except Exception as e:
             print(f"An unexpected error occurred for letter '{letter}': {e}")
             total_errors += 1

    print("\n--- Recipe Loading Complete ---")
    print(f"Total Recipes Added: {total_added}")
    print(f"Total Recipes Skipped (Already Existed): {total_skipped}")
    print(f"Total Errors Encountered: {total_errors}")


if __name__ == "__main__":
    main() 