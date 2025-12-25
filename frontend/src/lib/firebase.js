// src/lib/firebase.js
import { initializeApp } from "firebase/app";
import { getDatabase } from "firebase/database";
import { getAuth, GoogleAuthProvider } from "firebase/auth";

// REPLACE WITH YOUR ACTUAL FIREBASE PROJECT CONFIG
const firebaseConfig = {
    apiKey: "AIzaSyAViIs8bdZwePqdBplENkml0hHY6PwTktE",
    authDomain: "kriplani-builders.firebaseapp.com",
    databaseURL: "https://kriplani-builders-default-rtdb.asia-southeast1.firebasedatabase.app",
    projectId: "kriplani-builders",
    storageBucket: "kriplani-builders.firebasestorage.app",
    messagingSenderId: "338374704880",
    appId: "1:338374704880:web:a19847be2809948f748c35",
    measurementId: "G-SYDN2NK44Y"
};

// Initialize Firebase
const app = initializeApp(firebaseConfig);

// Initialize Services
const db = getDatabase(app);
const auth = getAuth(app);
const provider = new GoogleAuthProvider();

// Export functions for use in Svelte
// Export functions for use in Svelte
export { db, auth, provider };
export { ref, onValue, update, push } from "firebase/database";
export { signInWithPopup, signOut, onAuthStateChanged } from "firebase/auth";