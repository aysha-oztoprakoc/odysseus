import re
from pathlib import Path

content = Path("test_service_health.py").read_text()

# We need the shared imports and helpers
header = """\"\"\"Tests for src.service_health — split file.\"\"\"
import types
import pytest
from src import service_health as sh

def _resp(status_code):
    return types.SimpleNamespace(status_code=status_code)

def _raise(*_a, **_k):
    raise RuntimeError("connection refused")
"""

files = {
    "chromadb": [],
    "searxng": [],
    "ntfy": [],
    "email": [],
    "providers": [],
    "core": []
}

# The original _acct and _Conn for email:
email_helpers = """
def _acct(name, host="imap.example.com"):
    return {"account_id": name, "account_name": name, "imap_host": host,
            "imap_password": "hunter2"}

class _Conn:
    def logout(self):
        pass
"""

# The original _ep for providers:
providers_helpers = """
def _ep(name):
    return {"name": name, "base_url": f"http://{name}:8000/v1", "api_key": "sk-secret"}
"""

chromadb_helpers = """
class _Store:
    def __init__(self, healthy):
        self.healthy = healthy
"""

ntfy_helpers = """
def _ntfy_intg():
    return [{"preset": "ntfy", "enabled": True, "base_url": "http://ntfy:80"}]
"""

core_helpers = """
class _Store:
    def __init__(self, healthy):
        self.healthy = healthy
"""

files["email"].append(email_helpers)
files["providers"].append(providers_helpers)
files["chromadb"].append(chromadb_helpers)
files["ntfy"].append(ntfy_helpers)
files["core"].append(core_helpers)

# Simple regex-based line scanning
# We will identify which block we are in by the test name
lines = content.split('\n')
current_block = []
current_file = None

for line in lines:
    if line.startswith("def test_"):
        if "chromadb" in line: current_file = "chromadb"
        elif "searxng" in line: current_file = "searxng"
        elif "ntfy" in line: current_file = "ntfy"
        elif "email" in line: current_file = "email"
        elif "providers" in line: current_file = "providers"
        elif "rollup" in line or "collect" in line or "safe_url" in line or "classify" in line:
            current_file = "core"
        files[current_file].append(line)
    elif line.startswith("class _Store:") or line.startswith("def _Store"):
        pass # already added
    elif line.startswith("def _acct") or line.startswith("class _Conn") or line.startswith("def _ep") or line.startswith("def _ntfy_intg") or line.startswith("def _resp") or line.startswith("def _raise"):
        pass # already added
    elif line.startswith("@pytest.mark.parametrize"):
        # This is above a def test_, let's check next line
        pass # wait we need to capture decorators!
    elif line.startswith("# ──"):
        pass # section header
    else:
        if current_file and (line.startswith(" ") or line == "" or line.startswith("    ")):
            files[current_file].append(line)

# Let's do a more robust approach: regex extract complete function bodies.
