# Latency Ping Tracker

Simple tool to track and monitor network latency over time. Built this because I kept needing to check if my connection was actually the problem or if it was just "one of those days".

## Why

Sometimes your internet feels slow. Is it the ISP? The router? The DNS? This tool helps you actually know instead of just guessing while refreshing speedtest.net for the tenth time.

It pings hosts over time, stores the results, and gives you stats so you can spot patterns. Like "oh, latency spikes every day at 3pm" or "this DNS server is actually terrible".

## Quick Start

```bash
# Single ping test
python latency_tracker.py ping google.com

# Track a host (10 pings, 1 second apart)
python latency_tracker.py track 8.8.8.8

# Monitor multiple hosts
python latency_tracker.py monitor google.com cloudflare.com 1.1.1.1

# See report with stats
python latency_tracker.py report google.com

# List all tracked hosts
python latency_tracker.py list

# Export data to CSV for plotting
python latency_tracker.py export google.com
```

## Commands

| Command | Description |
|---------|-------------|
| `ping <host>` | Single ping, shows latency |
| `track <host>` | 10 measurements, good for quick checks |
| `monitor <hosts...>` | Monitor multiple hosts, 5 rounds |
| `report <host>` | Full stats report |
| `list` | Show all tracked hosts |
| `clear <host>` | Delete data for one host |
| `clear-all` | Wipe everything |
| `export <host>` | Save to CSV |
| `help` | Show help |

## Data Storage

All measurements go into `latency_data.json` in the current directory. It's just JSON so you can peek at it if you want. Each host keeps its own history with timestamps.

## Use Cases

**Check if your DNS is slow**
```bash
python latency_tracker.py monitor 8.8.8.8 1.1.1.9 208.67.222.222
```

**Track your gateway over time**
```bash
python latency_tracker.py track 192.168.1.1
```

**Compare CDN endpoints**
```bash
python latency_tracker.py monitor cdn1.example.com cdn2.example.com
```

**Long-term monitoring** (run in a loop)
```bash
while true; do
  python latency_tracker.py track your-server.com
  sleep 300
done
```

## Output Format

The `report` command shows:
- Total measurements
- Min/max/average latency
- Median (more useful than avg when you have spikes)
- Standard deviation (jitter)
- Recent 10 measurement average
- Warning if recent latency is elevated

## CSV Export

Export gives you a file like `google_com_latency.csv` with timestamp and latency columns. Drop it into a spreadsheet or plot it with whatever tool you like.

## Requirements

- Python 3.6+
- Linux/macOS (uses the `ping` command)
- No external packages needed

## Notes

- Uses system `ping` command under the hood
- Data persists between runs
- Timeout is 5 seconds per ping
- No fancy graphs built-in, but CSV export works with anything

## License

Do whatever you want with it.
