import subprocess
import pytest
from pathlib import Path

def test_pon_compliance_src():
    """
    Enforces the Notification-Oriented Paradigm (PON) zero-polling boundaries
    across the entire production source code using the kad_pon tester skill.
    We exclude the tests directory since test mocks legitimately use time.sleep
    to simulate network I/O delays.
    """
    script_path = Path.home() / "data_rein" / ".agents" / "skills" / "pon_testing_suite" / "scripts" / "pon_tester.py"
    target_path = Path.home() / "data_rein" / "src" / "reins"
    
    # Run PON tester on the harness source code
    result = subprocess.run(
        ["python3", str(script_path), str(target_path)],
        capture_output=True,
        text=True
    )
    
    assert result.returncode == 0, f"PON Compliance Failed on {target_path}:\n{result.stdout}\n{result.stderr}"


