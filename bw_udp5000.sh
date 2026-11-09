#!/usr/bin/env bash
# Passive UDP 5000 monitor. No traffic generation or port binding.
# Usage: sudo bash bw_udp5000.sh [INTERFACE] [SECONDS=30]
set -euo pipefail
[[ $EUID -eq 0 ]] || { echo "Run with sudo for packet capture." >&2; exit 1; }
for cmd in ip python3 tshark awk; do command -v "$cmd" >/dev/null; done
IFACE=${1:-$(ip -4 route show default | awk '{for(i=1;i<NF;i++) if($i=="dev") {print $(i+1); exit}}')}
[[ -n $IFACE ]] || { echo "Specify an interface, e.g. wlan0." >&2; exit 1; }
export TZ=${TZ:-Asia/Seoul}

exec python3 -u - "$IFACE" "${2:-30}" <<'PY'
import datetime, json, os, select, signal, subprocess, sys, time

interface = sys.argv[1]
try:
    seconds = int(sys.argv[2])
    if seconds < 0:
        raise ValueError
except ValueError:
    sys.exit('SECONDS must be a nonnegative integer; 0 means until Ctrl+C.')
addresses = json.loads(subprocess.check_output(
    ['ip', '-j', 'addr', 'show', 'dev', interface], text=True))
local_ips = {a['local'] for dev in addresses for a in dev['addr_info']}
if not local_ips:
    sys.exit('The selected interface has no IP address.')

command = ['tshark', '-n', '-l', '-p', '-i', interface,
           '-f', 'udp port 5000', '-T', 'fields', '-E', 'occurrence=f',
           '-e', 'ip.src', '-e', 'ipv6.src', '-e', 'frame.len']
if seconds:
    command += ['-a', f'duration:{seconds}']
print(f'Interface={interface} UDP=5000 Duration={seconds or "until Ctrl+C"}')
print('Time          TX_Mbps   RX_Mbps  TOTAL_Mbps  Window')
capture = subprocess.Popen(command, stdout=subprocess.PIPE)

def interrupted(*_):
    raise KeyboardInterrupt

signal.signal(signal.SIGTERM, interrupted)
tx = rx = 0
pending = b''
start = time.monotonic()
first = True

def report(note):
    global tx, rx, start
    now = time.monotonic()
    elapsed = now - start
    scale = 8 / elapsed / 1_000_000
    clock = datetime.datetime.now().strftime('%H:%M:%S')
    print(f'{clock}  {tx*scale:9.3f} {rx*scale:9.3f} '
          f'{(tx+rx)*scale:11.3f}  {note}', flush=True)
    tx = rx = 0
    start = now

try:
    while True:
        # A timer also prints 0 Mbps when no packets arrive.
        ready, _, _ = select.select(
            [capture.stdout], [], [], max(0, start + 1 - time.monotonic()))
        if ready:
            chunk = os.read(capture.stdout.fileno(), 65536)
            if not chunk:
                break
            pending += chunk
            while b'\n' in pending:
                line, pending = pending.split(b'\n', 1)
                fields = line.decode().rstrip('\r').split('\t')
                if len(fields) == 3 and fields[2].isdigit():
                    source = fields[0] or fields[1]
                    if source in local_ips:
                        tx += int(fields[2])
                    else:
                        rx += int(fields[2])
        if time.monotonic() - start >= 1:
            report('startup' if first else '1s')
            first = False
except KeyboardInterrupt:
    pass
finally:
    if capture.poll() is None:
        capture.terminate()
    try:
        code = capture.wait(timeout=5)
    except subprocess.TimeoutExpired:
        capture.kill()
        code = capture.wait()
    if tx or rx:
        report('partial-end')
    capture.stdout.close()
if code not in (0, -signal.SIGTERM, -signal.SIGINT):
    sys.exit(code if code > 0 else 1)
PY
