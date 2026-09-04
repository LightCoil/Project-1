from orchestrator.state import v56_autonomous_target
import project_status
def test_project_status():
    assert project_status() == "ACTIVE"