from autonomous_test_target import project_status


def test_project_status():
    assert project_status() == "NEW"
