#!/usr/bin/env python3
"""Expose current GitHub Actions job names from local Docker runner logs.

No external Python packages. Read-only Docker CLI; bind the HTTP listener to the
host's Lab IP or loopback, not the public interface. Logs may contain job names,
so restrict network access to Prometheus. This is an observed log-derived state,
not a GitHub API assertion of actual runner connectivity.
"""
import os
import re
import subprocess
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

RUNNERS = {
    'kc-gha-runner-local': 'kc',
    'dfair-gha-runner-local': 'dfair',
    'kc-timing-runner-local': 'kc_timing',
}
START = re.compile(r'(?:\d{4}-\d\d-\d\d[^ ]*\s+)?(?:\d{4}-\d\d-\d\d [0-9:]+Z:\s*)?Running job:\s*(.+)$')
END = re.compile(r'(?:\d{4}-\d\d-\d\d[^ ]*\s+)?(?:\d{4}-\d\d-\d\d [0-9:]+Z:\s*)?Job\s+(.+?)\s+completed with result:')
RESET = re.compile(r'Listening for Jobs|Container starting\.')


def escape_label(text):
    return text.replace('\\', '\\\\').replace('\n', '\\n').replace('"', '\\"')


def collect():
    lines = [
        '# HELP gha_runner_job_observer_up Whether Docker logs were read successfully (1=yes).',
        '# TYPE gha_runner_job_observer_up gauge',
        '# HELP gha_runner_current_job Current job inferred from runner logs (1=running).',
        '# TYPE gha_runner_current_job gauge',
        '# HELP gha_runner_job_observer_initialized Whether a runner start/idle marker was seen.',
        '# TYPE gha_runner_job_observer_initialized gauge',
    ]
    for container, runner in RUNNERS.items():
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
