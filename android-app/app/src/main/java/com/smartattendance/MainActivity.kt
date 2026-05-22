package com.smartattendance

import android.Manifest
import android.bluetooth.BluetoothAdapter
import android.bluetooth.BluetoothManager
import android.content.Intent
import android.content.pm.PackageManager
import android.os.Build
import android.os.Bundle
import android.util.Log
import android.widget.Button
import android.widget.TextView
import android.widget.Toast
import androidx.activity.result.contract.ActivityResultContracts
import androidx.appcompat.app.AppCompatActivity
import androidx.core.app.ActivityCompat
import androidx.core.content.ContextCompat
import com.google.firebase.auth.FirebaseAuth

class MainActivity : AppCompatActivity() {

    companion object {
        private const val TAG = "MainActivity"
        private const val PERMISSION_REQUEST_CODE = 100
    }

    private lateinit var auth: FirebaseAuth
    private lateinit var statusText: TextView
    private lateinit var userText: TextView
    private lateinit var scanButton: Button
    private lateinit var logoutButton: Button
    private lateinit var logText: TextView

    private var isScanning = false

    private val enableBluetoothLauncher = registerForActivityResult(
        ActivityResultContracts.StartActivityForResult()
    ) { result ->
        if (result.resultCode == RESULT_OK) {
            Log.d(TAG, "Bluetooth enabled")
            checkPermissionsAndStartScan()
        } else {
            Toast.makeText(this, "Bluetooth is required for attendance", Toast.LENGTH_LONG).show()
        }
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_main)

        auth = FirebaseAuth.getInstance()

        statusText = findViewById(R.id.textStatus)
        userText = findViewById(R.id.textUser)
        scanButton = findViewById(R.id.btnToggleScan)
        logoutButton = findViewById(R.id.btnLogout)
        logText = findViewById(R.id.textLog)

        auth.currentUser?.let { user ->
            userText.text = "Logged in as: ${user.email}"
        }

        scanButton.setOnClickListener {
            if (isScanning) {
                stopBleScanner()
            } else {
                checkPermissionsAndStartScan()
            }
        }

        logoutButton.setOnClickListener {
            stopBleScanner()
            auth.signOut()
            val intent = Intent(this, LoginActivity::class.java)
            intent.flags = Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TASK
            startActivity(intent)
            finish()
        }

        checkPermissionsAndStartScan()
    }

    
    private fun checkPermissionsAndStartScan() {
        val requiredPermissions = mutableListOf<String>()

        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S) {

            requiredPermissions.add(Manifest.permission.BLUETOOTH_SCAN)
            requiredPermissions.add(Manifest.permission.BLUETOOTH_CONNECT)
        }

        if (Build.VERSION.SDK_INT < Build.VERSION_CODES.S) {

            requiredPermissions.add(Manifest.permission.ACCESS_FINE_LOCATION)
        }

        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {

            requiredPermissions.add(Manifest.permission.POST_NOTIFICATIONS)
        }

        val missing = requiredPermissions.filter {
            ContextCompat.checkSelfPermission(this, it) != PackageManager.PERMISSION_GRANTED
        }

        if (missing.isNotEmpty()) {
            ActivityCompat.requestPermissions(
                this,
                missing.toTypedArray(),
                PERMISSION_REQUEST_CODE
            )
            return
        }

        val bluetoothManager = getSystemService(BLUETOOTH_SERVICE) as BluetoothManager
        val bluetoothAdapter = bluetoothManager.adapter

        if (bluetoothAdapter == null) {
            Toast.makeText(this, "BLE not supported on this device", Toast.LENGTH_LONG).show()
            return
        }

        if (!bluetoothAdapter.isEnabled) {
            val enableBtIntent = Intent(BluetoothAdapter.ACTION_REQUEST_ENABLE)
            enableBluetoothLauncher.launch(enableBtIntent)
            return
        }

        startBleScanner()
    }

    
    private fun startBleScanner() {
        val serviceIntent = Intent(this, BleScannerService::class.java)

        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            startForegroundService(serviceIntent)
        } else {
            startService(serviceIntent)
        }

        isScanning = true
        statusText.text = "🟢 Scanning Active"
        scanButton.text = "Stop Scanner"
        appendLog("BLE scanner service started")
        Log.d(TAG, "BLE scanner service started")
    }

    
    private fun stopBleScanner() {
        val serviceIntent = Intent(this, BleScannerService::class.java)
        stopService(serviceIntent)

        isScanning = false
        statusText.text = "🔴 Scanner Stopped"
        scanButton.text = "Start Scanner"
        appendLog("BLE scanner service stopped")
        Log.d(TAG, "BLE scanner service stopped")
    }

    
    private fun appendLog(message: String) {
        val timestamp = java.text.SimpleDateFormat("HH:mm:ss", java.util.Locale.getDefault())
            .format(java.util.Date())
        logText.append("[$timestamp] $message\n")
    }

    
    override fun onRequestPermissionsResult(
        requestCode: Int,
        permissions: Array<out String>,
        grantResults: IntArray
    ) {
        super.onRequestPermissionsResult(requestCode, permissions, grantResults)

        if (requestCode == PERMISSION_REQUEST_CODE) {
            if (grantResults.all { it == PackageManager.PERMISSION_GRANTED }) {
                checkPermissionsAndStartScan()
            } else {
                Toast.makeText(
                    this,
                    "Permissions required for BLE attendance scanning",
                    Toast.LENGTH_LONG
                ).show()
            }
        }
    }
}
