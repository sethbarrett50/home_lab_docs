#!/usr/bin/env python3
"""Read-only Prometheus exporter for a single NVIDIA GPU via nvidia-smi."""

import subprocess
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

HOST = "192.168.10.162"
PORT = 9835
FIELDS = {
    "utilization.gpu": ("nvidia_gpu_utilization_percent", "GPU utilization"),
    "memory.used": ("nvidia_gpu_memory_used_bytes", "GPU memory used"),
    "memory.total": ("nvidia_gpu_memory_total_bytes", "GPU memory total"),
    "temperature.gpu": ("nvidia_gpu_temperature_celsius", "GPU temperature"),
    "power.draw": ("nvidia_gpu_power_watts", "GPU power draw"),
}
ORDER = list(FIELDS)
MIB = 1024 * 1024


def collect():
    result = subprocess.run(
        ["/usr/bin/nvidia-smi", "--query-gpu=" + ",".join(ORDER),
         "--format=csv,noheader,nounits"],
        capture_output=True, text=True, check=True, timeout=8,
    )
    lines = result.stdout.strip().splitlines()
    if len(lines) != 1:
        raise ValueError("Expected exactly one GPU")
    values = [part.strip() for part in lines[0].split(",")]
    if len(values) != len(ORDER):
        raise ValueError("Unexpected NVIDIA output")

    metrics = []
    for field, raw in zip(ORDER, values, strict=True):
        name, description = FIELDS[field]
        value = float(raw)
        if field.startswith("memory."):
            value *= MIB
        metrics.extend([
            f"# HELP {name} {description}",
            f"# TYPE {name} gauge",
            f'{name}{{gpu="0"}} {value}',
        ])
    processes = subprocess.run(
        ["/usr/bin/nvidia-smi", "--query-compute-apps=pid",
         "--format=csv,noheader,nounits"],
        capture_output=True, text=True, check=True, timeout=8,
    )
    count = sum(line.strip().isdigit() for line in processes.stdout.splitlines())
    metrics.extend([
        "# HELP nvidia_gpu_compute_processes Active GPU compute processes",
        "# TYPE nvidia_gpu_compute_processes gauge",
        f'nvidia_gpu_compute_processes{{gpu="0"}} {count}',
    ])
    return "\n".join(metrics) + "\n"


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path != "/metrics":
            self.send_error(404)
            return
        try:
            body = collect().encode()
        except (OSError, ValueError, subprocess.SubprocessError) as exc:
            self.send_error(503, "GPU collection failed")
            print(f"GPU collection failed: {exc}", flush=True)
            return
        self.send_response(200)
        self.send_header("Content-Type", "text/plain; version=0.0.4")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


if __name__ == "__main__":
    ThreadingHTTPServer((HOST, PORT), Handler).serve_forever()
