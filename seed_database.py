import os
import requests
from dotenv import load_dotenv
from supabase import create_client, Client
import time # To add delays between API calls if needed

def fetch_recipes_by_letter(letter: str, supabase: Client):
    """Fetches recipes starting with a specific letter from TheMealDB and inserts them."""
    api_url = f"https://www.themealdb.com/api/json/v1/1/search.php?f={letter}"
    headers = {'Accept': 'application/json'} 
    recipes_to_insert = []
    print(f"Fetching recipes starting with '{letter}'...")

    try:
        response = requests.get(api_url, headers=headers)
        response.raise_for_status() 
        data = response.json()

        if data and data.get('meals'):
            for meal in data['meals']:
                # Data Mapping & Transformation
                ingredients = []
                for i in range(1, 21):
                    ingredient = meal.get(f'strIngredient{i}')
                    if ingredient and ingredient.strip():
                        # Just add lowercased ingredient name for our text[] column
                        ingredients.append(ingredient.strip().lower())
                    else:
                        break 

                recipe_data = {
                    'name': meal.get('strMeal'),
                    'description': f"Category: {meal.get('strCategory')}, Area: {meal.get('strArea')}",
                    'instructions': meal.get('strInstructions'),
                    'image_url': meal.get('strMealThumb'),
                    'ingredients': ingredients 
                }
                
                # Basic validation
                if recipe_data['name'] and recipe_data['ingredients']:
                    # Optional: Check if recipe name already exists to avoid duplicates
                    # check = supabase.table('recipes').select('id').eq('name', recipe_data['name']).limit(1).execute()
                    # if not check.data:
                    recipes_to_insert.append(recipe_data)
                else:
                    print(f"Skipping meal due to missing name or ingredients: {meal.get('strMeal')}")

            # Insert into Supabase in batches (or all at once if not too many)
            if recipes_to_insert:
                print(f"Attempting to insert {len(recipes_to_insert)} recipes for letter '{letter}'...")
                try:
                    insert_response = supabase.table('recipes').insert(recipes_to_insert).execute()
                    # Check response structure - may differ slightly based on client version
                    # Basic check: See if data is present
                    if insert_response.data:
                        print(f"Successfully processed batch for letter '{letter}'. Response count: {len(insert_response.data)}")
                    else:
                        print(f"Insertion for letter '{letter}' finished, but response data is empty (might be ok, or might indicate issue).")
                except Exception as db_error:
                    print(f"Database insertion error for letter '{letter}': {db_error}")
                    # Consider logging individual failing recipes if needed

        else:
            print(f"No meals found for letter '{letter}' in API response.")

    except requests.exceptions.RequestException as e:
        print(f"API request failed for letter '{letter}': {e}")
    except Exception as e:
        print(f"An unexpected error occurred for letter '{letter}': {e}")

def main():
    """Main function to load environment variables, connect to Supabase, and fetch recipes."""
    load_dotenv()

    supabase_url = os.environ.get("SUPABASE_URL")
    # supabase_key = os.environ.get("SUPABASE_ANON_KEY") # Use anon key for RLS - COMMENTED OUT
    supabase_key = os.environ.get("SUPABASE_SERVICE_KEY") # Use Service Role Key instead

    if not supabase_url or not supabase_key:
        # print("Error: SUPABASE_URL and SUPABASE_ANON_KEY env vars required.") # Old error message
        print("Error: SUPABASE_URL and SUPABASE_SERVICE_KEY env vars required.") # Updated error message
        return

    try:
        supabase: Client = create_client(supabase_url, supabase_key)
        print("Supabase client initialized.")

        # --- Choose which letters to fetch --- 
        # Fetch for a specific letter:
        # fetch_recipes_by_letter('a', supabase)
        
        # Fetch for multiple letters (add delays to be nice to the API):
        letters_to_fetch = ['a', 'b', 'c', 'd', 'e'] # Add more letters as needed
        for letter in letters_to_fetch:
            fetch_recipes_by_letter(letter, supabase)
            print("Waiting 1 second before next letter...")
            time.sleep(1) # Be polite to the free API
        
        print("Seeding process finished.")

    except Exception as e:
        print(f"Failed to initialize Supabase client or run main process: {e}")

if __name__ == "__main__":
    main() 