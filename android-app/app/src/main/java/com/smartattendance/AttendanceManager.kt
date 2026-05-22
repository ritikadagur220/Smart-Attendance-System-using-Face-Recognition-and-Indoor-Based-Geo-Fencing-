package com.smartattendance

import android.content.Context
import android.util.Log
import com.google.firebase.auth.FirebaseAuth
import com.google.firebase.firestore.FirebaseFirestore
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale

class AttendanceManager(private val context: Context) {

    companion object {
        private const val TAG = "AttendanceManager"
    }

    private val firestore = FirebaseFirestore.getInstance()
    private val auth = FirebaseAuth.getInstance()

    private var currentStatus: String = AppConfig.STATUS_EXIT
    private var lastDetectionTime: Long = 0L
    private var lastExitTime: Long = 0L
    private var activeDocumentId: String? = null
    private var studentId: String? = null
    private var studentName: String? = null

    init {

        loadStudentInfo()
    }

    
    private fun loadStudentInfo() {
        val uid = auth.currentUser?.uid ?: return

        firestore.collection(AppConfig.COLLECTION_STUDENTS)
            .whereEqualTo("id", uid)
            .limit(1)
            .get()
            .addOnSuccessListener { docs ->
                for (doc in docs) {
                    studentId = doc.getString("id") ?: uid
                    studentName = doc.getString("name") ?: auth.currentUser?.email ?: "Unknown"
                    Log.d(TAG, "Student loaded: $studentName ($studentId)")
                }
                if (studentId == null) {

                    studentId = uid
                    studentName = auth.currentUser?.email ?: "Unknown"
                    Log.w(TAG, "Student not found in Firestore, using auth info")
                }
            }
            .addOnFailureListener { e ->
                Log.e(TAG, "Failed to load student info", e)
                studentId = uid
                studentName = auth.currentUser?.email ?: "Unknown"
            }
    }

    
    fun processBeaconSignal(rssi: Int) {
        val now = System.currentTimeMillis()
        lastDetectionTime = now

        Log.d(TAG, "Processing signal: RSSI=$rssi, currentStatus=$currentStatus")

        when {

            rssi > AppConfig.RSSI_THRESHOLD_PRESENT -> {
                if (currentStatus != AppConfig.STATUS_PRESENT) {

                    if (lastExitTime > 0 && (now - lastExitTime) < AppConfig.DUPLICATE_WINDOW_MS) {
                        val remaining = (AppConfig.DUPLICATE_WINDOW_MS - (now - lastExitTime)) / 1000
                        Log.d(TAG, "DUPLICATE BLOCKED: Re-entry blocked, wait ${remaining}s")
                        return
                    }
                    markPresent(rssi)
                } else {
                    Log.d(TAG, "ALREADY PRESENT: No action needed")
                }
            }

            rssi < AppConfig.RSSI_THRESHOLD_EXIT -> {
                if (currentStatus == AppConfig.STATUS_PRESENT) {
                    markExit()
                } else {
                    Log.d(TAG, "NOT PRESENT: Exit signal ignored")
                }
            }

            else -> {
                Log.d(TAG, "HYSTERESIS: RSSI=$rssi in dead zone, no state change")
            }
        }
    }

    
    fun checkExitTimeout() {
        if (currentStatus != AppConfig.STATUS_PRESENT) return
        if (lastDetectionTime == 0L) return

        val elapsed = System.currentTimeMillis() - lastDetectionTime
        if (elapsed > AppConfig.EXIT_TIMEOUT_MS) {
            Log.d(TAG, "AUTO-EXIT: Timeout after ${elapsed / 1000}s")
            markExit()
        }
    }

    
    private fun markPresent(rssi: Int) {
        if (studentId == null) {
            Log.e(TAG, "Cannot mark present: studentId is null")
            return
        }

        val dateFormat = SimpleDateFormat("yyyy-MM-dd", Locale.getDefault())
        val timeFormat = SimpleDateFormat("yyyy-MM-dd'T'HH:mm:ss", Locale.getDefault())
        val now = Date()

        val attendanceData = hashMapOf(
            "student_id" to studentId,
            "student_name" to studentName,
            "entry_time" to timeFormat.format(now),
            "exit_time" to null,
            "status" to AppConfig.STATUS_PRESENT,
            "date" to dateFormat.format(now),
            "classroom" to "Room-101",
            "rssi" to rssi,
        )

        firestore.collection(AppConfig.COLLECTION_ATTENDANCE)
            .add(attendanceData)
            .addOnSuccessListener { docRef ->
                activeDocumentId = docRef.id
                currentStatus = AppConfig.STATUS_PRESENT
                Log.d(TAG, "✅ MARKED PRESENT: $studentName (doc: ${docRef.id})")
            }
            .addOnFailureListener { e ->
                Log.e(TAG, "❌ Failed to mark present", e)
            }
    }

    
    private fun markExit() {
        val docId = activeDocumentId
        if (docId == null) {
            Log.w(TAG, "No active document to update for exit")
            currentStatus = AppConfig.STATUS_EXIT
            lastExitTime = System.currentTimeMillis()
            return
        }

        val timeFormat = SimpleDateFormat("yyyy-MM-dd'T'HH:mm:ss", Locale.getDefault())

        firestore.collection(AppConfig.COLLECTION_ATTENDANCE)
            .document(docId)
            .update(
                mapOf(
                    "exit_time" to timeFormat.format(Date()),
                    "status" to AppConfig.STATUS_EXIT,
                )
            )
            .addOnSuccessListener {
                currentStatus = AppConfig.STATUS_EXIT
                lastExitTime = System.currentTimeMillis()
                activeDocumentId = null
                Log.d(TAG, "🚪 MARKED EXIT: $studentName")
            }
            .addOnFailureListener { e ->
                Log.e(TAG, "❌ Failed to mark exit", e)

                currentStatus = AppConfig.STATUS_EXIT
                lastExitTime = System.currentTimeMillis()
                activeDocumentId = null
            }
    }
}
