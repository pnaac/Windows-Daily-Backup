// src/lib/firebase.js
import { initializeApp } from "firebase/app";
import { getDatabase, ref, onValue, update } from "firebase/database";

// PASTE YOUR CONFIG HERE
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

const app = initializeApp(firebaseConfig);
const db = getDatabase(app);

export { db, ref, onValue, update };