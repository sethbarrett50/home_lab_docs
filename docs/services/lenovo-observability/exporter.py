#!/usr/bin/env python3
"""Expose current GitHub Actions job names from local Docker runner logs.

No external Python packages. Read-only Docker CLI; bind the HTTP listener to the
host's Lab IP or loopback, not the public interface. Logs may contain job names,
so restrict network access to Prometheus. This is an observed log-derived state,
not a GitHub API assertion of actual runner connectivity.
"""
import json
import os
import re
import subprocess
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

RUNNERS = {
    'kc-backend-runner-local': 'kc_backend',
    'kc-infra-runner-local': 'kc_infra',
}
START = re.compile(r'(?:\d{4}-\d\d-\d\d[^ ]*\s+)?(?:\d{4}-\d\d-\d\d [0-9:]+Z:\s*)?Running job:\s*(.+)$')
END = re.compile(r'(?:\d{4}-\d\d-\d\d[^ ]*\s+)?(?:\d{4}-\d\d-\d\d [0-9:]+Z:\s*)?Job\s+(.+?)\s+completed with result:')
RESET = re.compile(r'Listening for Jobs|Container starting\.')


def escape_label(text):
    return text.replace('\\', '\\\\').replace('\n', '\\n').replace('"', '\\"')


def parse_bytes(value):
    """Parse Docker stats memory amounts (B, KiB, MiB, GiB, etc.)."""
    match = re.fullmatch(r'\\s*([0-9]+(?:\\.[0-9]+)?)\\s*([KMGTPE]?i?B|B)\\s*', value)
    if not match:
        raise ValueError(f'Unrecognized Docker memory unit: {value!r}')
    amount = float(match.group(1))
    unit = match.group(2)
    prefixes = {'': 0, 'K': 1, 'M': 2, 'G': 3, 'T': 4, 'P': 5, 'E': 6}
    prefix = '' if unit == 'B' else unit[0]
    return amount * ((1024 if 'iB' in unit else 1000) ** prefixes[prefix])


def collect_stats():
    """Get host-relative CPU and RAM percentages from Docker in one read."""
    cmd = ['docker', 'stats', '--no-stream', '--format', '{{json .}}', *RUNNERS]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=12)
        if result.returncode != 0:
            return {}
        total_kb = next(
            int(line.split()[1]) for line in open('/proc/meminfo')
            if line.startswith('MemTotal:')
        )
        host_memory = total_kb * 1024
        host_cpus = os.cpu_count() or 1
        parsed = {}
        for line in result.stdout.splitlines():
            entry = json.loads(line)
            name = entry.get('Name')
            if name not in RUNNERS:
                continue
            cpu = float(entry['CPUPerc'].strip().removesuffix('%')) / host_cpus
            used = entry['MemUsage'].split('/')[0].strip()
            memory = 100 * parse_bytes(used) / host_memory
            parsed[name] = (cpu, memory)
        return parsed
    except (OSError, ValueError, KeyError, StopIteration, subprocess.TimeoutExpired, json.JSONDecodeError):
        return {}


def collect():
    lines = [
        '# HELP gha_runner_job_observer_up Whether Docker logs were read successfully (1=yes).',
        '# TYPE gha_runner_job_observer_up gauge',
        '# HELP gha_runner_current_job Current job inferred from runner logs (1=running).',
        '# TYPE gha_runner_current_job gauge',
        '# HELP gha_runner_job_observer_initialized Whether a runner start/idle marker was seen.',
        '# TYPE gha_runner_job_observer_initialized gauge',
        '# HELP gha_runner_container_running Whether Docker reports the named container running.',
        '# TYPE gha_runner_container_running gauge',
        '# HELP gha_runner_container_stats_up Whether Docker stats returned valid usage metrics.',
        '# TYPE gha_runner_container_stats_up gauge',
        '# HELP gha_runner_container_cpu_host_percent Docker CPU usage as percent of total host logical CPU capacity.',
        '# TYPE gha_runner_container_cpu_host_percent gauge',
        '# HELP gha_runner_container_memory_host_percent Docker memory usage as percent of host physical memory.',
        '# TYPE gha_runner_container_memory_host_percent gauge',
    ]
    stats = collect_stats()
    for container, runner in RUNNERS.items():
        lines.append(f'gha_runner_container_stats_up{{runner="{runner}"}} {int(container in stats)}')
        if container in stats:
            cpu, memory = stats[container]
            lines.append(f'gha_runner_container_cpu_host_percent{{runner="{runner}"}} {cpu:.5f}')
            lines.append(f'gha_runner_container_memory_host_percent{{runner="{runner}"}} {memory:.5f}')
        # A running container is not the same as an online GitHub runner.
        # Keep this independent from the log observer for clearer diagnostics.
        try:
            state = subprocess.run(
                ['docker', 'inspect', '--format', '{{.State.Running}}', container],
                capture_output=True, text=True, timeout=5,
            )
            running = int(state.returncode == 0 and state.stdout.strip() == 'true')
        except (OSError, subprocess.TimeoutExpired):
            running = 0
        lines.append(f'gha_runner_container_running{{runner="{runner}"}} {running}')
        try:
            result = subprocess.run(['docker', 'logs', '--tail', '20000', container],
                                    capture_output=True, text=True, timeout=8)
            if result.returncode != 0:
                raise RuntimeError(result.stderr[:120])
            job = None
            initialized = False
            for line in result.stdout.splitlines() + result.stderr.splitlines():
                # Docker logs normally writes container stdout to stdout; avoid
                # treating Docker daemon error text as valid observations.
                if RESET.search(line):
                    job, initialized = None, True
                match = START.search(line)
                if match:
                    job, initialized = match.group(1).strip(), True
                match = END.search(line)
                if match and job == match.group(1).strip():
                    job = None
            lines.append(f'gha_runner_job_observer_up{{runner="{runner}"}} 1')
            lines.append(f'gha_runner_job_observer_initialized{{runner="{runner}"}} {int(initialized)}')
            if job:
                lines.append(f'gha_runner_current_job{{runner="{runner}",job="{escape_label(job)}"}} 1')
        except (OSError, subprocess.TimeoutExpired, RuntimeError):
            lines.append(f'gha_runner_job_observer_up{{runner="{runner}"}} 0')
            lines.append(f'gha_runner_job_observer_initialized{{runner="{runner}"}} 0')
    return ('\n'.join(lines) + '\n').encode()


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path != '/metrics':
            self.send_error(404)
            return
        data = collect()
        self.send_response(200)
        self.send_header('Content-Type', 'text/plain; version=0.0.4; charset=utf-8')
        self.send_header('Content-Length', str(len(data)))
        self.end_headers()
        self.wfile.write(data)


if __name__ == '__main__':
    host = os.environ.get('EXPORTER_LISTEN', '127.0.0.1')
    port = int(os.environ.get('EXPORTER_PORT', '9119'))
    ThreadingHTTPServer((host, port), Handler).serve_forever()
