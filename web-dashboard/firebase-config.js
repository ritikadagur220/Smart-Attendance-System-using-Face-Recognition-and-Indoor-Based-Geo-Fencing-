

const firebaseConfig = {
    apiKey: "YOUR_API_KEY",
    authDomain: "YOUR_PROJECT_ID.firebaseapp.com",
    projectId: "YOUR_PROJECT_ID",
    storageBucket: "YOUR_PROJECT_ID.appspot.com",
    messagingSenderId: "YOUR_SENDER_ID",
    appId: "YOUR_APP_ID"
};

try {
    if (firebaseConfig.apiKey !== "YOUR_API_KEY") {
        firebase.initializeApp(firebaseConfig);
        console.log("✅ Firebase initialized");
    } else {
        console.warn("⚠️ Firebase not configured — running in DEMO mode");
        console.warn("   Edit firebase-config.js with your project credentials");
    }
} catch (error) {
    console.error("❌ Firebase initialization error:", error);
}
