#!/usr/bin/env python3
"""
Latency Ping Tracker - Monitor network latency over time
"""

import subprocess
import json
import time
import statistics
from datetime import datetime
from pathlib import Path
from typing import Optional


DATA_FILE = Path("latency_data.json")


def ping_host(host: str, timeout: int = 5) -> Optional[float]:
    """Ping a host and return latency in milliseconds."""
    try:
        result = subprocess.run(
            ["ping", "-c", "1", "-W", str(timeout), host],
            capture_output=True,
            text=True,
            timeout=timeout + 2
        )
        if result.returncode != 0:
            return None
        
        output = result.stdout
        if "time=" in output:
            time_part = output.split("time=")[1].split()[0]
            latency = float(time_part.replace("ms", ""))
            return latency
        return None
    except (subprocess.TimeoutExpired, ValueError, IndexError):
        return None


def load_data() -> dict:
    """Load existing latency data from file."""
    if DATA_FILE.exists():
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    return {"hosts": {}}


def save_data(data: dict) -> None:
    """Save latency data to file."""
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=2)


def record_latency(host: str, latency: float) -> None:
    """Record a latency measurement for a host."""
    data = load_data()
    
    if host not in data["hosts"]:
        data["hosts"][host] = {
            "measurements": [],
            "created_at": datetime.now().isoformat()
        }
    
    measurement = {
        "timestamp": datetime.now().isoformat(),
        "latency_ms": latency
    }
    data["hosts"][host]["measurements"].append(measurement)
    save_data(data)


def get_statistics(host: str) -> Optional[dict]:
    """Calculate statistics for a host's latency measurements."""
    data = load_data()
    
    if host not in data["hosts"]:
        return None
    
    measurements = data["hosts"][host]["measurements"]
    if not measurements:
        return None
    
    latencies = [m["latency_ms"] for m in measurements]
    
    return {
        "count": len(latencies),
        "min": min(latencies),
        "max": max(latencies),
        "avg": statistics.mean(latencies),
        "median": statistics.median(latencies),
        "stdev": statistics.stdev(latencies) if len(latencies) > 1 else 0.0,
        "last": latencies[-1]
    }


def list_hosts() -> list:
    """List all tracked hosts."""
    data = load_data()
    return list(data["hosts"].keys())


def clear_host_data(host: str) -> bool:
    """Clear all data for a specific host."""
    data = load_data()
    
    if host in data["hosts"]:
        del data["hosts"][host]
        save_data(data)
        return True
    return False


def clear_all_data() -> None:
    """Clear all tracked data."""
    save_data({"hosts": {}})


def run_monitoring_session(hosts: list, count: int, interval: float) -> None:
    """Run a monitoring session for specified hosts."""
    print(f"Starting monitoring session for {len(hosts)} host(s)")
    print(f"Will collect {count} measurements per host")
    print(f"Interval between measurements: {interval}s")
    print("-" * 50)
    
    for i in range(count):
        print(f"\n[Round {i + 1}/{count}] {datetime.now().strftime('%H:%M:%S')}")
        
        for host in hosts:
            latency = ping_host(host)

            if latency is not None:
                record_latency(host, latency)
                print(f"  {host}: {latency:.2f}ms [OK]")
            else:
                print(f"  {host}: TIMEOUT")
        
        if i < count - 1:
            time.sleep(interval)
    
    print("\n" + "=" * 50)
    print("Session complete. Summary:")
    
    for host in hosts:
        stats = get_statistics(host)
        if stats:
            print(f"\n{host}:")
            print(f"  Measurements: {stats['count']}")
            print(f"  Min: {stats['min']:.2f}ms")
            print(f"  Max: {stats['max']:.2f}ms")
            print(f"  Avg: {stats['avg']:.2f}ms")
            print(f"  Median: {stats['median']:.2f}ms")
            if stats['stdev'] > 0:
                print(f"  Std Dev: {stats['stdev']:.2f}ms")


def show_report(host: str) -> None:
    """Show detailed report for a host."""
    stats = get_statistics(host)
    
    if not stats:
        print(f"No data available for host: {host}")
        return
    
    data = load_data()
    created = data["hosts"][host].get("created_at", "unknown")
    
    print(f"\nLatency Report for: {host}")
    print("=" * 40)
    print(f"Tracking since: {created}")
    print(f"Total measurements: {stats['count']}")
    print("-" * 40)
    print(f"Current:  {stats['last']:.2f}ms")
    print(f"Minimum:  {stats['min']:.2f}ms")
    print(f"Maximum:  {stats['max']:.2f}ms")
    print(f"Average:  {stats['avg']:.2f}ms")
    print(f"Median:   {stats['median']:.2f}ms")
    if stats['stdev'] > 0:
        print(f"Std Dev:  {stats['stdev']:.2f}ms")
    
    if stats['count'] >= 10:
        recent = [m["latency_ms"] for m in data["hosts"][host]["measurements"][-10:]]
        recent_avg = statistics.mean(recent)
        print(f"\nRecent 10 avg: {recent_avg:.2f}ms")
        
        if recent_avg > stats['avg'] * 1.2:
            print("WARNING: Recent latency is elevated!")
        elif recent_avg < stats['avg'] * 0.8:
            print("NOTE: Recent latency is better than average")


def export_csv(host: str) -> str:
    """Export host data to CSV format."""
    data = load_data()
    
    if host not in data["hosts"]:
        return ""
    
    lines = ["timestamp,latency_ms"]
    for m in data["hosts"][host]["measurements"]:
        lines.append(f"{m['timestamp']},{m['latency_ms']}")
    
    filename = f"{host.replace('.', '_')}_latency.csv"
    with open(filename, "w") as f:
        f.write("\n".join(lines))
    
    return filename


def print_help():
    """Print help information."""
    help_text = """
Latency Ping Tracker - Network Latency Monitoring Tool

Usage:
  python latency_tracker.py <command> [options]

Commands:
  ping <host>              Single ping test
  track <host>             Track one host (10 pings, 1s interval)
  monitor <host1> [host2]  Monitor multiple hosts
  report <host>            Show detailed report for a host
  list                     List all tracked hosts
  clear <host>             Clear data for a host
  clear-all                Clear all tracked data
  export <host>            Export host data to CSV
  help                     Show this help

Examples:
  python latency_tracker.py ping google.com
  python latency_tracker.py track 8.8.8.8
  python latency_tracker.py monitor google.com cloudflare.com
  python latency_tracker.py report google.com
  python latency_tracker.py export google.com
"""
    print(help_text)


def main():
    import sys
    
    if len(sys.argv) < 2:
        print_help()
        return
    
    command = sys.argv[1].lower()
    
    if command == "help":
        print_help()
    
    elif command == "ping":
        if len(sys.argv) < 3:
            print("Usage: python latency_tracker.py ping <host>")
            return
        host = sys.argv[2]
        latency = ping_host(host)
        if latency is not None:
            print(f"{host}: {latency:.2f}ms")
        else:
            print(f"{host}: TIMEOUT")
    
    elif command == "track":
        if len(sys.argv) < 3:
            print("Usage: python latency_tracker.py track <host>")
            return
        host = sys.argv[2]
        run_monitoring_session([host], count=10, interval=1.0)
    
    elif command == "monitor":
        if len(sys.argv) < 3:
            print("Usage: python latency_tracker.py monitor <host1> [host2] ...")
            return
        hosts = sys.argv[2:]
        run_monitoring_session(hosts, count=5, interval=2.0)
    
    elif command == "report":
        if len(sys.argv) < 3:
            print("Usage: python latency_tracker.py report <host>")
            return
        host = sys.argv[2]
        show_report(host)
    
    elif command == "list":
        hosts = list_hosts()
        if hosts:
            print("Tracked hosts:")
            for h in hosts:
                stats = get_statistics(h)
                if stats:
                    print(f"  - {h} ({stats['count']} measurements, avg: {stats['avg']:.2f}ms)")
        else:
            print("No hosts tracked yet")
    
    elif command == "clear":
        if len(sys.argv) < 3:
            print("Usage: python latency_tracker.py clear <host>")
            return
        host = sys.argv[2]
        if clear_host_data(host):
            print(f"Cleared data for: {host}")
        else:
            print(f"No data found for: {host}")
    
    elif command == "clear-all":
        confirm = input("Clear all tracked data? (yes/no): ")
        if confirm.lower() == "yes":
            clear_all_data()
            print("All data cleared")
        else:
            print("Cancelled")
    
    elif command == "export":
        if len(sys.argv) < 3:
            print("Usage: python latency_tracker.py export <host>")
            return
        host = sys.argv[2]
        filename = export_csv(host)
        if filename:
            print(f"Exported to: {filename}")
        else:
            print(f"No data to export for: {host}")
    
    else:
        print(f"Unknown command: {command}")
        print_help()


if __name__ == "__main__":
    main()
