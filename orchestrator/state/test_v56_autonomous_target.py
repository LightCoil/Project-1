from orchestrator.state import v56_autonomous_target


def test_project_status():
    assert v56_autonomous_target.project_status() == "ACTIVE"
