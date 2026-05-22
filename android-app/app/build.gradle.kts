// ============================================================
//  Smart Attendance System - App-level build.gradle (Kotlin DSL)
//  
//  NOTE: This is a reference build file. You will need to:
//  1. Create the project in Android Studio (File → New → New Project)
//  2. Choose "Empty Activity" template
//  3. Set package name to: com.smartattendance
//  4. Replace the generated build.gradle with this file
//  5. Add google-services.json from Firebase Console
// ============================================================

plugins {
    id("com.android.application")
    id("org.jetbrains.kotlin.android")
    id("com.google.gms.google-services")  // Firebase
}

android {
    namespace = "com.smartattendance"
    compileSdk = 34

    defaultConfig {
        applicationId = "com.smartattendance"
        minSdk = 26          // Android 8.0 minimum (for foreground service)
        targetSdk = 34
        versionCode = 1
        versionName = "1.0.0"
    }

    buildTypes {
        release {
            isMinifyEnabled = false
            proguardFiles(
                getDefaultProguardFile("proguard-android-optimize.txt"),
                "proguard-rules.pro"
            )
        }
    }

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_1_8
        targetCompatibility = JavaVersion.VERSION_1_8
    }

    kotlinOptions {
        jvmTarget = "1.8"
    }
}

dependencies {
    // AndroidX Core
    implementation("androidx.core:core-ktx:1.12.0")
    implementation("androidx.appcompat:appcompat:1.6.1")
    implementation("com.google.android.material:material:1.11.0")
    implementation("androidx.constraintlayout:constraintlayout:2.1.4")
    implementation("androidx.activity:activity-ktx:1.8.2")

    // Firebase BoM (Bill of Materials) — manages all Firebase version
    implementation(platform("com.google.firebase:firebase-bom:32.7.0"))

    // Firebase Auth
    implementation("com.google.firebase:firebase-auth-ktx")

    // Firebase Firestore
    implementation("com.google.firebase:firebase-firestore-ktx")

    // Testing
    testImplementation("junit:junit:4.13.2")
    androidTestImplementation("androidx.test.ext:junit:1.1.5")
}
