package com.smartattendance

object AppConfig {

    const val BLE_DEVICE_NAME = "ER-BLEV2.3-26D0008"

    const val RSSI_THRESHOLD_PRESENT = -75
    const val RSSI_THRESHOLD_EXIT = -85

    const val SCAN_INTERVAL_MS = 5000L
    const val SCAN_DURATION_MS = 4000L
    const val EXIT_TIMEOUT_MS = 30000L
    const val DUPLICATE_WINDOW_MS = 60000L

    const val NOTIFICATION_CHANNEL_ID = "ble_scanner_channel"
    const val NOTIFICATION_CHANNEL_NAME = "BLE Scanner Service"
    const val NOTIFICATION_ID = 1001

    const val COLLECTION_STUDENTS = "students"
    const val COLLECTION_ATTENDANCE = "attendance"
    const val COLLECTION_BEACONS = "beacons"

    const val STATUS_PRESENT = "PRESENT"
    const val STATUS_EXIT = "EXIT"
}
