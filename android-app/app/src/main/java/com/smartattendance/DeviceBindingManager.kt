package com.smartattendance

import android.content.Context
import android.provider.Settings
import android.util.Log
import com.google.firebase.auth.FirebaseAuth
import com.google.firebase.firestore.FirebaseFirestore

class DeviceBindingManager(private val context: Context) {

    companion object {
        private const val TAG = "DeviceBindingManager"
        private const val PREFS_NAME = "smart_attendance_prefs"
        private const val KEY_DEVICE_BOUND = "device_bound"
    }

    private val firestore = FirebaseFirestore.getInstance()
    private val auth = FirebaseAuth.getInstance()

    
    fun getDeviceId(): String {
        return Settings.Secure.getString(
            context.contentResolver,
            Settings.Secure.ANDROID_ID
        ) ?: "unknown-device"
    }

    
    fun isDeviceBound(): Boolean {
        val prefs = context.getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE)
        return prefs.getBoolean(KEY_DEVICE_BOUND, false)
    }

    
    fun bindDevice(onSuccess: () -> Unit, onFailure: (String) -> Unit) {
        val uid = auth.currentUser?.uid
        if (uid == null) {
            onFailure("User not authenticated")
            return
        }

        val deviceId = getDeviceId()
        Log.d(TAG, "Binding device: $deviceId to user: $uid")

        firestore.collection(AppConfig.COLLECTION_STUDENTS)
            .document(uid)
            .update("device_id", deviceId)
            .addOnSuccessListener {

                val prefs = context.getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE)
                prefs.edit().putBoolean(KEY_DEVICE_BOUND, true).apply()

                Log.d(TAG, "✅ Device bound successfully: $deviceId")
                onSuccess()
            }
            .addOnFailureListener { e ->
                Log.e(TAG, "❌ Device binding failed", e)
                onFailure(e.message ?: "Unknown error")
            }
    }

    
    fun verifyDevice(onVerified: (Boolean) -> Unit) {
        val uid = auth.currentUser?.uid
        if (uid == null) {
            onVerified(false)
            return
        }

        val currentDeviceId = getDeviceId()

        firestore.collection(AppConfig.COLLECTION_STUDENTS)
            .document(uid)
            .get()
            .addOnSuccessListener { doc ->
                val boundDeviceId = doc.getString("device_id")
                val matches = boundDeviceId == currentDeviceId
                
                if (!matches) {
                    Log.w(TAG, "⚠️ Device mismatch: bound=$boundDeviceId, current=$currentDeviceId")
                }
                
                onVerified(matches)
            }
            .addOnFailureListener { e ->
                Log.e(TAG, "Device verification failed", e)
                onVerified(false)
            }
    }

    
    fun clearBinding() {
        val prefs = context.getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE)
        prefs.edit().remove(KEY_DEVICE_BOUND).apply()
        Log.d(TAG, "Device binding cleared")
    }
}
