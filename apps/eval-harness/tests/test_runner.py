from rasenloop_eval.runner import run_suite


def test_offline_suite_passes_blockers():
    report = run_suite(transport_mode="fake")
    assert report["passed"] is True
    assert report["blocker_failures"] == []
    assert len(report["scenarios"]) >= 8
