package com.smartattendance

import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.app.Service
import android.bluetooth.BluetoothManager
import android.bluetooth.le.BluetoothLeScanner
import android.bluetooth.le.ScanCallback
import android.bluetooth.le.ScanFilter
import android.bluetooth.le.ScanResult
import android.bluetooth.le.ScanSettings
import android.content.Intent
import android.os.Build
import android.os.Handler
import android.os.IBinder
import android.os.Looper
import android.os.PowerManager
import android.util.Log
import androidx.core.app.NotificationCompat

class BleScannerService : Service() {

    companion object {
        private const val TAG = "BleScannerService"
    }

    private var bluetoothLeScanner: BluetoothLeScanner? = null
    private lateinit var attendanceManager: AttendanceManager
    private lateinit var handler: Handler
    private var wakeLock: PowerManager.WakeLock? = null
    private var isScanning = false

    override fun onCreate() {
        super.onCreate()
        Log.d(TAG, "Service created")

        attendanceManager = AttendanceManager(this)
        handler = Handler(Looper.getMainLooper())

        val bluetoothManager = getSystemService(BLUETOOTH_SERVICE) as BluetoothManager
        bluetoothLeScanner = bluetoothManager.adapter?.bluetoothLeScanner

        val powerManager = getSystemService(POWER_SERVICE) as PowerManager
        wakeLock = powerManager.newWakeLock(
            PowerManager.PARTIAL_WAKE_LOCK,
            "SmartAttendance::BleScannerWakeLock"
        )
        wakeLock?.acquire(4 * 60 * 60 * 1000L)
    }

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        Log.d(TAG, "Service started")

        createNotificationChannel()
        startForeground(AppConfig.NOTIFICATION_ID, buildNotification("Scanning for classroom beacon..."))

        startScanCycle()

        return START_STICKY
    }

    override fun onDestroy() {
        Log.d(TAG, "Service destroyed")
        stopScanCycle()
        wakeLock?.let {
            if (it.isHeld) it.release()
        }
        super.onDestroy()
    }

    override fun onBind(intent: Intent?): IBinder? = null

    
    private fun startScanCycle() {
        startBleScan()
    }

    
    private fun startBleScan() {
        if (isScanning) return

        val scanner = bluetoothLeScanner
        if (scanner == null) {
            Log.e(TAG, "BluetoothLeScanner is null — BLE not available")
            return
        }

        try {

            val filters = listOf(
                ScanFilter.Builder()
                    .setDeviceName(AppConfig.BLE_DEVICE_NAME)
                    .build()
            )

            val settings = ScanSettings.Builder()
                .setScanMode(ScanSettings.SCAN_MODE_LOW_LATENCY)
                .setReportDelay(0)
                .build()

            scanner.startScan(filters, settings, scanCallback)
            isScanning = true
            Log.d(TAG, "BLE scan started")

            handler.postDelayed({
                stopBleScan()

                attendanceManager.checkExitTimeout()

                handler.postDelayed({
                    startBleScan()
                }, AppConfig.SCAN_INTERVAL_MS - AppConfig.SCAN_DURATION_MS)

            }, AppConfig.SCAN_DURATION_MS)

        } catch (e: SecurityException) {
            Log.e(TAG, "SecurityException: Missing BLE permissions", e)
        } catch (e: Exception) {
            Log.e(TAG, "Error starting BLE scan", e)
        }
    }

    
    private fun stopBleScan() {
        if (!isScanning) return

        try {
            bluetoothLeScanner?.stopScan(scanCallback)
            isScanning = false
            Log.d(TAG, "BLE scan stopped")
        } catch (e: SecurityException) {
            Log.e(TAG, "SecurityException stopping scan", e)
        }
    }

    
    private fun stopScanCycle() {
        handler.removeCallbacksAndMessages(null)
        stopBleScan()
    }

    
    private val scanCallback = object : ScanCallback() {

        override fun onScanResult(callbackType: Int, result: ScanResult) {
            super.onScanResult(callbackType, result)

            val device = result.device
            val rssi = result.rssi
            val deviceName = result.scanRecord?.deviceName ?: device?.name ?: ""

            Log.d(TAG, "Device detected: name=$deviceName, rssi=$rssi, address=${device?.address}")

            if (deviceName == AppConfig.BLE_DEVICE_NAME) {
                attendanceManager.processBeaconSignal(rssi)
                updateNotification("Beacon detected — RSSI: ${rssi}dBm")
            }
        }

        override fun onScanFailed(errorCode: Int) {
            super.onScanFailed(errorCode)
            Log.e(TAG, "BLE scan failed with error code: $errorCode")
            updateNotification("Scan error (code: $errorCode)")
        }
    }

    
    private fun createNotificationChannel() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            val channel = NotificationChannel(
                AppConfig.NOTIFICATION_CHANNEL_ID,
                AppConfig.NOTIFICATION_CHANNEL_NAME,
                NotificationManager.IMPORTANCE_LOW
            ).apply {
                description = "BLE scanner is running for attendance tracking"
                setShowBadge(false)
            }

            val manager = getSystemService(NotificationManager::class.java)
            manager.createNotificationChannel(channel)
        }
    }

    
    private fun buildNotification(contentText: String): Notification {
        val pendingIntent = PendingIntent.getActivity(
            this, 0,
            Intent(this, MainActivity::class.java),
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE
        )

        return NotificationCompat.Builder(this, AppConfig.NOTIFICATION_CHANNEL_ID)
            .setContentTitle("Smart Attendance")
            .setContentText(contentText)
            .setSmallIcon(android.R.drawable.ic_dialog_info)
            .setContentIntent(pendingIntent)
            .setOngoing(true)
            .setSilent(true)
            .build()
    }

    
    private fun updateNotification(text: String) {
        val manager = getSystemService(NotificationManager::class.java)
        manager.notify(AppConfig.NOTIFICATION_ID, buildNotification(text))
    }
}
