// Replace with your Firebase config
const firebaseConfig = {
    apiKey: "AIzaSyD4GpP3Z5rqBmGvBJUvYnOmtkeKtfOK3ws",
    authDomain: "recime-e3113.firebaseapp.com",
    projectId: "recime-e3113",
    storageBucket: "recime-e3113.firebasestorage.app",
    messagingSenderId: "947457498360",
    appId: "1:947457498360:web:80b84e949e7fb48d962f0d",
    measurementId: "G-3Y8JYY63S7"
};

  // Initialize Firebase app and services
  const app = firebase.initializeApp(firebaseConfig);
  const db = firebase.firestore();
  const auth = firebase.auth(); // Initialize Firebase Authentication

  // Get DOM elements
  const ingredientInput = document.getElementById('ingredientInput');
  const searchButton = document.getElementById('searchButton');
  const resultsDiv = document.getElementById('results');

  // Get Authentication related DOM elements.
  const emailInput = document.getElementById('email');
  const passwordInput = document.getElementById('password');
  const signupButton = document.getElementById('signupButton');
  const loginButton = document.getElementById('loginButton');
  const logoutButton = document.getElementById('logoutButton');
  const authContainer = document.getElementById('auth-container');
  const savedRecipesList = document.getElementById('saved-recipes-list');

  // Modified updateUI() function
  function updateUI(user) {
    if (user) {
      authContainer.style.display = 'none';
      logoutButton.style.display = 'block !important';
      document.getElementById('saved-recipes').style.display = 'block';
      displaySavedRecipes(user.uid);
    } else {
      authContainer.style.display = 'block';
      logoutButton.style.display = 'none !important';
      document.getElementById('saved-recipes').style.display = 'none';
      savedRecipesList.innerHTML = "";
    }
  }

  // Authentication: User signup
  signupButton.addEventListener('click', () => {
    auth.createUserWithEmailAndPassword(emailInput.value, passwordInput.value)
      .then((userCredential) => {
        console.log('User signed up:', userCredential.user);
        updateUI(userCredential.user); // Directly update UI
      })
      .catch((error) => {
        console.error('Signup error:', error);
        alert(error.message);
      });
  });

  // Authentication: User login
  loginButton.addEventListener('click', () => {
    auth.signInWithEmailAndPassword(emailInput.value, passwordInput.value)
      .then((userCredential) => {
        console.log('User logged in:', userCredential.user);
        updateUI(userCredential.user); // Directly update UI
      })
      .catch((error) => {
        console.error('Login error:', error);
        alert(error.message);
      });
  });

  // Authentication: User logout
  logoutButton.addEventListener('click', () => {
    auth.signOut()
      .then(() => {
        console.log('User logged out');
        updateUI(null); // Directly update UI
      })
      .catch((error) => {
        console.error('Logout error:', error);
        alert(error.message);
      });
  });

  // Save recipe function
  function saveRecipe(recipeId) {
    auth.onAuthStateChanged((user) => {
      if (user) {
        db.collection('saved_recipes').add({ // Save recipe to the 'saved_recipes' collection
          userId: user.uid,
          recipeId: recipeId,
          savedAt: firebase.firestore.FieldValue.serverTimestamp()
        }).then(() => {
          displaySavedRecipes(user.uid);
        });
      }
    });
  }

  // Display saved recipes
  function displaySavedRecipes(userId) {
    savedRecipesList.innerHTML = '';
    if(!userId) return;
    db.collection('saved_recipes').where('userId', '==', userId).get().then((querySnapshot) => { // Query saved recipes for the current user
      querySnapshot.forEach((doc) => {
        const savedRecipe = doc.data();
        db.collection('recipes').doc(savedRecipe.recipeId).get().then((recipeDoc) => { // Fetch the recipe details
          const recipe = recipeDoc.data();
          const recipeDiv = document.createElement('div');
          recipeDiv.innerHTML = `
          <h3>${recipe.title}</h3>
          <img src="${recipe.image}" alt="${recipe.title}" style="max-width: 200px; max-height: 200px;">
          <p>Ingredients: ${recipe.ingredients.join(', ')}</p>
          <p>Instructions: ${recipe.instructions}</p>
          <hr>
          `;
          savedRecipesList.appendChild(recipeDiv);
        });
      });
    });
  }

  // Search for recipes based on ingredients
  searchButton.addEventListener('click', () => {
    const ingredient = ingredientInput.value.toLowerCase();
    resultsDiv.innerHTML = ''; // Clear previous results

    db.collection('recipes').get().then((querySnapshot) => { // Fetch all recipes from the 'recipes' collection
      querySnapshot.forEach((doc) => {
        const recipe = doc.data();
        if (recipe.ingredients.map(item => item.toLowerCase()).includes(ingredient)) { // Check if the ingredient is in the recipe's ingredients
          const recipeDiv = document.createElement('div');
          recipeDiv.innerHTML = `
            <h3>${recipe.title}</h3>
            <img src="${recipe.image}" alt="${recipe.title}" style="max-width: 200px; max-height: 200px;">
            <p>Ingredients: ${recipe.ingredients.join(', ')}</p>
            <p>Instructions: ${recipe.instructions}</p>
            <button onclick="saveRecipe('${doc.id}')">Save Recipe</button>
            <hr>
          `;
          resultsDiv.appendChild(recipeDiv);
        }
      });
    });
  });

  // Set initial UI state
  updateUI(auth.currentUser);