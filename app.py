import os # Import os for environment variables
from dotenv import load_dotenv # Import dotenv
from supabase import create_client, Client # Import Supabase
from flask import Flask, render_template, request, redirect, url_for, session, flash

load_dotenv() # Load environment variables from .env file

app = Flask(__name__)
# You should replace this with a real secret key in a production environment
app.secret_key = os.environ.get('FLASK_SECRET_KEY', 'a-fallback-secret-key') # Use env var for secret key

# Initialize Supabase
supabase_url: str = os.environ.get("SUPABASE_URL")
supabase_key: str = os.environ.get("SUPABASE_ANON_KEY")

# Check if Supabase credentials are provided
if not supabase_url or not supabase_key:
    print("Error: SUPABASE_URL and SUPABASE_ANON_KEY environment variables are required.")
    # Depending on your setup, you might want to exit or handle this differently
    # exit(1) 
    supabase: Client | None = None # Set supabase to None if keys are missing
else:
    supabase: Client = create_client(supabase_url, supabase_key)

@app.route('/')
def home():
    # Check if user is logged in
    if 'user' not in session:
        return redirect(url_for('login')) # Redirect to login if not logged in

    recipes = []
    user_email = session['user'].get('email', 'User') # Get email safely
    
    if supabase:
        try:
            # Fetch all recipes from the 'recipes' table, ordered by creation date
            response = supabase.table('recipes').select('*').order('created_at', desc=True).execute()
            recipes = response.data
        except Exception as e:
            print(f"Error fetching recipes: {e}")
            # You might want to pass an error message to the template here

    # Pass the fetched recipes and user email to the template
    return render_template('index.html', email=user_email, recipes=recipes)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        # Basic placeholder for login/signup logic
        # In a real app, you'd verify credentials or create a new user
        email = request.form.get('email') # Change from username to email for Supabase auth
        password = request.form.get('password') # Remember to hash passwords!
        action = request.form.get('action') # 'login' or 'signup'
        
        if not supabase:
             return render_template('login.html', error='Supabase not configured')

        try:
            if action == 'login':
                print(f"Attempting login for user: {email}")
                # Use Supabase auth for login
                user_response = supabase.auth.sign_in_with_password({"email": email, "password": password})
                # Store Supabase session details in Flask session
                session['user'] = user_response.user.model_dump()
                session['access_token'] = user_response.session.access_token
                return redirect(url_for('home'))

            elif action == 'signup':
                print(f"Attempting signup for user: {email}")
                # Use Supabase auth for signup
                user_response = supabase.auth.sign_up({"email": email, "password": password})
                # Auto-login: Store Supabase session details in Flask session after signup
                # Note: Supabase might require email confirmation depending on your project settings
                session['user'] = user_response.user.model_dump()
                session['access_token'] = user_response.session.access_token
                return redirect(url_for('home'))

        except Exception as e:
            print(f"Supabase auth error: {e}")
            # Provide a generic error message to the user
            error_message = "An error occurred during authentication. Please check your credentials or try again."
            # You might want to inspect the specific error 'e' for more details
            # For example, check for specific Supabase error types if the library provides them
            # If str(e).contains("Invalid login credentials") -> error_message = "Invalid email or password."
            # If str(e).contains("User already registered") -> error_message = "Email already registered."
            # etc.
            return render_template('login.html', error=error_message)

    # If GET request or failed POST, show the login page
    # Check if user is already logged in via Flask session
    if 'user' in session:
        return redirect(url_for('home'))
    return render_template('login.html')

@app.route('/logout')
def logout():
    if 'access_token' in session and supabase:
        try:
            # Sign out from Supabase
            supabase.auth.sign_out()
        except Exception as e:
            print(f"Supabase sign out error: {e}")
    # Clear the Flask session regardless
    session.pop('user', None)
    session.pop('access_token', None)
    return redirect(url_for('login'))

@app.route('/saved_recipes')
def saved_recipes():
    print("--- Accessing /saved_recipes route ---") # DEBUG
    if 'user' not in session or not supabase:
        print("--- User not in session or Supabase unavailable, redirecting to login ---") # DEBUG
        return redirect(url_for('login'))

    user_id = session['user'].get('id') # Get user ID safely
    if not user_id:
        print("--- User ID not found in session ---") # DEBUG
        flash('Could not identify user session.', 'error')
        return redirect(url_for('login'))
        
    print(f"--- Fetching saved recipes for user_id: {user_id} ---") # DEBUG
    
    user_saved_recipes = [] # Initialize list to hold recipe details
    try:
        # Fetch records from saved_recipes matching the user_id
        # And also fetch ALL data (*) from the related recipe using the foreign key relationship
        print("--- Executing Supabase query for saved recipes ---") # DEBUG
        response = supabase.table('saved_recipes')\
                         .select('recipe_id, recipes(*)')\
                         .eq('user_id', user_id)\
                         .execute()
        
        print(f"--- Supabase response status: {response.status_code if hasattr(response, 'status_code') else 'N/A'} ---") # DEBUG
        print(f"--- Raw Supabase response data: {response.data} ---") # DEBUG
        
        # The result (response.data) is a list of dictionaries like:
        # [ { "recipe_id": "uuid1", "recipes": { recipe details dict } }, ... ]
        # We need to extract just the recipe details dictionary
        if response.data:
            user_saved_recipes = [item['recipes'] for item in response.data if item.get('recipes')] # Extract recipe details safely
            print(f"--- Extracted {len(user_saved_recipes)} saved recipe details ---") # DEBUG
        else:
            print("--- No saved recipe data returned from Supabase ---") # DEBUG
            
    except Exception as e:
        print(f"--- Error fetching saved recipes for user {user_id}: {e} ---") # DEBUG
        flash('An error occurred while fetching your saved recipes.', 'error') # Inform user

    # Pass the list of saved recipe details to the template
    print(f"--- Rendering saved_recipes.html with {len(user_saved_recipes)} recipes ---") # DEBUG
    return render_template('saved_recipes.html', recipes=user_saved_recipes)

@app.route('/view_recipe/<uuid:recipe_id>') # Use uuid converter for recipe_id
def view_recipe(recipe_id):
    if 'user' not in session or not supabase:
        return redirect(url_for('login'))

    recipe_details = None
    is_saved = False # Flag to check if user has saved this recipe
    user_id = session['user']['id']

    try:
        # Fetch the specific recipe by its UUID
        response = supabase.table('recipes').select('*').eq('id', str(recipe_id)).single().execute()
        recipe_details = response.data
    except Exception as e:
        print(f"Error fetching recipe details for id {recipe_id}: {e}")

    # If recipe details were found, check if the current user has saved it
    if recipe_details:
        try:
            # Check for an entry in saved_recipes matching user_id and recipe_id
            # We only need to know if it exists, so select 'recipe_id' and use .limit(1)
            saved_check = supabase.table('saved_recipes')\
                                .select('recipe_id', count='exact')\
                                .eq('user_id', user_id)\
                                .eq('recipe_id', str(recipe_id))\
                                .limit(1)\
                                .execute()
            # If count > 0, the user has saved this recipe
            if saved_check.count > 0:
                is_saved = True
        except Exception as e:
            print(f"Error checking saved status for user {user_id}, recipe {recipe_id}: {e}")
            # Proceed assuming not saved if check fails

    if not recipe_details:
        flash('Recipe not found.', 'error') # Use flash message
        return redirect(url_for('home')) # Redirect home if recipe not found
        
    # Pass the fetched details and saved status to the template
    return render_template('view_recipe.html', recipe=recipe_details, is_saved=is_saved)

@app.route('/save_recipe/<uuid:recipe_id>', methods=['POST'])
def save_recipe(recipe_id):
    if 'user' not in session or not supabase:
        return redirect(url_for('login'))

    user_id = session['user']['id']
    
    try:
        # Insert into saved_recipes table
        # The RLS policy ensures user_id matches auth.uid()
        supabase.table('saved_recipes').insert({
            'user_id': user_id,
            'recipe_id': str(recipe_id)
        }).execute()
        flash('Recipe saved successfully!', 'success')
    except Exception as e:
        print(f"Error saving recipe {recipe_id} for user {user_id}: {e}")
        # Exception might occur if already saved (unique constraint) or other DB issues
        flash('Error saving recipe. It might already be saved.', 'error')

    # Redirect back to the recipe detail page
    return redirect(url_for('view_recipe', recipe_id=recipe_id))

@app.route('/unsave_recipe/<uuid:recipe_id>', methods=['POST'])
def unsave_recipe(recipe_id):
    if 'user' not in session or not supabase:
        return redirect(url_for('login'))

    user_id = session['user']['id']

    try:
        # Delete from saved_recipes table
        # RLS policy ensures user can only delete their own entries
        supabase.table('saved_recipes')\
            .delete()\
            .eq('user_id', user_id)\
            .eq('recipe_id', str(recipe_id))\
            .execute()
        flash('Recipe unsaved successfully!', 'success')
    except Exception as e:
        print(f"Error unsaving recipe {recipe_id} for user {user_id}: {e}")
        flash('Error unsaving recipe.', 'error')

    # Redirect back to the recipe detail page
    return redirect(url_for('view_recipe', recipe_id=recipe_id))

@app.route('/search')
def search():
    # Get list of ingredients from query parameters (e.g., ?ingredients[]=egg&ingredients[]=flour)
    ingredients_query = request.args.getlist('ingredients[]') 
    print(f"--- Search started with query: {ingredients_query} ---") # DEBUG
    if not ingredients_query:
        print("--- No ingredients in query, redirecting to home ---") # DEBUG
        return redirect(url_for('home'))
    
    # Clean and filter ingredients: remove whitespace, convert to lowercase, remove empty strings
    search_ingredients = [ing.strip().lower() for ing in ingredients_query if ing.strip()]
    if not search_ingredients: # If all inputs were empty/whitespace
        print("--- All ingredients were empty/whitespace, redirecting to home ---") # DEBUG
        flash('Please enter at least one valid ingredient.', 'error')
        return redirect(url_for('home'))
    
    print(f"--- Cleaned search ingredients: {search_ingredients} ---") # DEBUG
        
    if not supabase:
        print("--- Supabase client not available ---") # DEBUG
        flash('Database connection not available.', 'error')
        # Render results page showing the ingredients searched for, even with error
        return render_template('search_results.html', recipes=[], search_ingredients=search_ingredients)

    matching_recipes = []
    try:
        print("--- Fetching all recipes from database for multi-ingredient search ---") # DEBUG
        response = supabase.table('recipes').select('*').execute()
        all_recipes = response.data or []
        print(f"--- Fetched {len(all_recipes)} recipes total ---") # DEBUG
        
        # Filter recipes: Find recipes containing ALL search_ingredients
        for recipe in all_recipes:
            recipe_name = recipe.get('name', 'Unnamed Recipe') # DEBUG
            ingredients_data = recipe.get('ingredients')
            
            recipe_ingredients_set = set() # Use a set for efficient lookup
            if isinstance(ingredients_data, list):
                recipe_ingredients_set = {str(ing).strip().lower() for ing in ingredients_data if str(ing).strip()}
            elif isinstance(ingredients_data, str):
                recipe_ingredients_set = {ing.strip().lower() for ing in ingredients_data.split(',') if ing.strip()}
            
            # print(f"--- Checking Recipe: '{recipe_name}', Parsed Ingredients Set: {recipe_ingredients_set} ---") # DEBUG - Can be noisy

            # Check if all search_ingredients are present in the recipe's ingredients
            if all(search_ing in recipe_ingredients_set for search_ing in search_ingredients):
                print(f"--- Match found! Recipe '{recipe_name}' contains all: {search_ingredients} ---") # DEBUG
                matching_recipes.append(recipe)
            # else: # DEBUG - Optional
            #      print(f"--- No match: Recipe '{recipe_name}' does not contain all of {search_ingredients} (Recipe has: {recipe_ingredients_set}) ---")
                
    except Exception as e:
        print(f"--- Error during multi-ingredient recipe search: {e} ---") # DEBUG
        flash('An error occurred during the search.', 'error')

    print(f"--- Multi-ingredient search complete. Found {len(matching_recipes)} matching recipes for {search_ingredients}. Rendering results page. ---") # DEBUG
    return render_template('search_results.html', recipes=matching_recipes, search_ingredients=search_ingredients)

# --- Add Profile Route --- 
@app.route('/profile')
def profile():
    if 'user' not in session:
        return redirect(url_for('login'))

    # Get user info from session (add more fields if you store them later)
    user_info = {
        'email': session['user'].get('email', 'N/A'),
        'id': session['user'].get('id'),
        'last_sign_in_at': session['user'].get('last_sign_in_at') # Example field
    }
    
    return render_template('profile.html', user=user_info)

# --- Routes for Creating Recipes ---
@app.route('/create_recipe', methods=['GET', 'POST'])
def create_recipe():
    if 'user' not in session:
        return redirect(url_for('login'))

    if request.method == 'POST':
        if not supabase:
            flash('Database connection not available.', 'error')
            return render_template('create_recipe.html') # Show form again

        # --- Process Form Data ---
        try:
            recipe_name = request.form.get('name', '').strip()
            description = request.form.get('description', '').strip()
            instructions = request.form.get('instructions', '').strip()
            image_url = request.form.get('image_url', '').strip() or None # Use None if empty
            
            # Process ingredients (assuming one per line in textarea)
            ingredients_raw = request.form.get('ingredients', '').strip()
            ingredients_list = [ing.strip().lower() for ing in ingredients_raw.splitlines() if ing.strip()]

            # Basic Validation
            if not recipe_name:
                flash('Recipe name is required.', 'error')
                # Re-render form with submitted data (except ingredients list)
                return render_template('create_recipe.html', 
                                        name=recipe_name, description=description, 
                                        instructions=instructions, image_url=image_url,
                                        ingredients_raw=ingredients_raw)
            
            # --- Insert into Supabase ---
            response = supabase.table('recipes').insert({
                'name': recipe_name,
                'description': description,
                'ingredients': ingredients_list, # Pass the python list
                'instructions': instructions,
                'image_url': image_url
                # 'created_by': session['user']['id'] # Optional: Add a column to track creator
            }).execute()

            # Check if insert was successful (Supabase client v2+ doesn't raise error on duplicate but might return different data)
            # A more robust check might be needed depending on exact client behavior
            if response.data: 
                flash('Recipe created successfully!', 'success')
                # Redirect to the new recipe's page (need the new ID)
                # The response usually contains the inserted data including the new ID
                new_recipe_id = response.data[0]['id']
                return redirect(url_for('view_recipe', recipe_id=new_recipe_id))
            else:
                 flash('Failed to create recipe. Please try again.', 'error')

        except Exception as e:
            print(f"Error creating recipe: {e}")
            flash(f"An error occurred while creating the recipe: {e}", "error")
        
        # If error occurred, re-render form with submitted data
        return render_template('create_recipe.html', 
                                name=request.form.get('name'), 
                                description=request.form.get('description'), 
                                instructions=request.form.get('instructions'), 
                                image_url=request.form.get('image_url'),
                                ingredients_raw=request.form.get('ingredients'))

    # --- Handle GET Request (Show Form) ---
    else: 
        return render_template('create_recipe.html')

if __name__ == '__main__':
    # Use debug=True for development, it enables auto-reloading and detailed error pages
    # Ensure debug=False in a production environment
    app.run(debug=True) 