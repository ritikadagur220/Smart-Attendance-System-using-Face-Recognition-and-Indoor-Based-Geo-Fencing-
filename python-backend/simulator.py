"""
============================================================
  Smart Attendance System - BLE Event Simulator
  Simulates BLE scan events to test the attendance engine
  without real hardware.
============================================================
"""

import time
import sys

try:
    from colorama import init, Fore, Style
    init(autoreset=True)
except ImportError:

    class Fore:
        GREEN = RED = YELLOW = CYAN = MAGENTA = WHITE = RESET = ""
    class Style:
        BRIGHT = RESET_ALL = ""

from attendance_engine import AttendanceEngine
from config import BLE_DEVICE_NAME, DEFAULT_CLASSROOM

def print_header(text: str):
    """Print a formatted section header."""
    print(f"\n{'=' * 60}")
    print(f"  {Fore.CYAN}{Style.BRIGHT}{text}")
    print(f"{'=' * 60}")

def print_result(result: dict):
    """Print a formatted event result."""
    action = result["action"]
    color = {
        "MARKED_PRESENT": Fore.GREEN,
        "MARKED_EXIT": Fore.RED,
        "ALREADY_PRESENT": Fore.YELLOW,
        "DUPLICATE_BLOCKED": Fore.YELLOW,
        "REJECTED": Fore.RED,
        "NO_CHANGE": Fore.WHITE,
        "NOT_PRESENT": Fore.WHITE,
        "AUTO_EXIT": Fore.MAGENTA,
    }.get(action, Fore.WHITE)

    icon = {
        "MARKED_PRESENT": "[OK]",
        "MARKED_EXIT": "[EXIT]",
        "ALREADY_PRESENT": "[WARN]",
        "DUPLICATE_BLOCKED": "[BLOCK]",
        "REJECTED": "[DENY]",
        "NO_CHANGE": "[--]",
        "NOT_PRESENT": "[??]",
        "AUTO_EXIT": "[TIMEOUT]",
    }.get(action, "*")

    print(f"  {icon} {color}{action:<20}{Style.RESET_ALL} | {result['message']}")

def simulate_event(engine: AttendanceEngine, device_name: str, rssi: int, device_id: str, label: str = ""):
    """Simulate a single BLE event."""
    if label:
        print(f"\n  {Fore.MAGENTA}> {label}{Style.RESET_ALL}")
    print(f"    [BLE] Device: {device_name} | RSSI: {rssi}dBm | DeviceID: {device_id}")
    result = engine.process_ble_event(device_name, rssi, device_id, DEFAULT_CLASSROOM)
    print_result(result)
    return result

def run_simulation():
    """Run the complete BLE attendance simulation."""
    engine = AttendanceEngine()

    print_header("PHASE 0: DEVICE REGISTRATION")
    engine.register_device("AA:BB:CC:DD:EE:01", "STU001", "Ritik Kumar")
    engine.register_device("AA:BB:CC:DD:EE:02", "STU002", "Priya Sharma")
    engine.register_device("AA:BB:CC:DD:EE:03", "STU003", "Amit Singh")
    print(f"  {Fore.GREEN}[OK] 3 devices registered successfully{Style.RESET_ALL}")

    print_header("SCENARIO 1: Normal Entry - Strong Signal")

    simulate_event(
        engine, BLE_DEVICE_NAME, -60, "AA:BB:CC:DD:EE:01",
        "Ritik walks into classroom (strong signal)"
    )

    simulate_event(
        engine, BLE_DEVICE_NAME, -55, "AA:BB:CC:DD:EE:02",
        "Priya walks into classroom (strong signal)"
    )

    print_header("SCENARIO 2: Duplicate Prevention")

    simulate_event(
        engine, BLE_DEVICE_NAME, -65, "AA:BB:CC:DD:EE:01",
        "Ritik detected again (already present)"
    )

    print_header("SCENARIO 3: Unknown Device Rejection")

    simulate_event(
        engine, BLE_DEVICE_NAME, -50, "XX:YY:ZZ:00:00:00",
        "Unknown device attempts attendance"
    )

    print_header("SCENARIO 4: Wrong Beacon Name")

    simulate_event(
        engine, "WRONG-BEACON-NAME", -50, "AA:BB:CC:DD:EE:01",
        "Signal from wrong beacon"
    )

    print_header("SCENARIO 5: Hysteresis Zone - No State Change")

    simulate_event(
        engine, BLE_DEVICE_NAME, -80, "AA:BB:CC:DD:EE:01",
        "Ritik near door (RSSI in hysteresis zone: -75 to -85)"
    )

    print_header("SCENARIO 6: Exit Detection - Weak Signal")

    simulate_event(
        engine, BLE_DEVICE_NAME, -90, "AA:BB:CC:DD:EE:01",
        "Ritik walks out of classroom (weak signal)"
    )

    simulate_event(
        engine, BLE_DEVICE_NAME, -95, "AA:BB:CC:DD:EE:02",
        "Priya walks out of classroom (weak signal)"
    )

    print_header("SCENARIO 7: Re-entry Within Duplicate Window")

    simulate_event(
        engine, BLE_DEVICE_NAME, -60, "AA:BB:CC:DD:EE:01",
        "Ritik tries to re-enter immediately (within 60s window)"
    )

    print_header("SCENARIO 8: Exit for Non-Present Student")

    simulate_event(
        engine, BLE_DEVICE_NAME, -90, "AA:BB:CC:DD:EE:03",
        "Amit gets weak signal but was never present"
    )

    print_header("SCENARIO 9: New Student Entry")

    simulate_event(
        engine, BLE_DEVICE_NAME, -50, "AA:BB:CC:DD:EE:03",
        "Amit walks into classroom (strong signal)"
    )

    print_header("SCENARIO 10: Timeout-Based Auto Exit")
    print(f"  {Fore.YELLOW}[WAIT] Simulating timeout (overriding last_seen)...{Style.RESET_ALL}")

    engine._last_seen["STU003"] = time.time() - 60
    auto_exits = engine.check_exit_timeouts()
    for exit_result in auto_exits:
        print_result(exit_result)
    if not auto_exits:
        print(f"  {Fore.WHITE}  No timeouts detected{Style.RESET_ALL}")

    print_header("SIMULATION SUMMARY")

    summary = engine.get_attendance_summary()
    print(f"  [STATS] Active Students: {summary['active_count']}")
    print(f"  [STATS] Total Sessions Today: {len(engine.get_history())}")

    if summary["active_students"]:
        print(f"\n  {Fore.GREEN}Currently Present:{Style.RESET_ALL}")
        for s in summary["active_students"]:
            print(f"    - {s['student_name']} (since {s['entry_time']}, RSSI: {s['rssi']}dBm)")

    history = engine.get_history()
    if history:
        print(f"\n  {Fore.CYAN}Completed Sessions:{Style.RESET_ALL}")
        for record in history:
            entry = record.entry_time.strftime("%H:%M:%S")
            exit_t = record.exit_time.strftime("%H:%M:%S") if record.exit_time else "N/A"
            dur = int(record.duration_seconds())
            print(f"    - {record.student_name}: {entry} -> {exit_t} ({dur}s)")

    print(f"\n  {Fore.CYAN}Event Log:{Style.RESET_ALL}")
    for log_entry in engine.get_event_log():
        ts = log_entry["timestamp"].split("T")[1][:8]
        print(f"    [{ts}] {log_entry['message']}")

    print(f"\n{'=' * 60}")
    print(f"  {Fore.GREEN}{Style.BRIGHT}[OK] SIMULATION COMPLETE - All scenarios tested!")
    print(f"{'=' * 60}\n")

if __name__ == "__main__":
    run_simulation()
