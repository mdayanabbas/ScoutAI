from app.jobs.expansion.hiring_scope_detector import HiringScopeDetector


def test_hiring_scope_detector_core_scopes():
    detector = HiringScopeDetector()

    assert detector.detect(title="GTM Team").scope_type == "gtm"
    assert detector.detect(title="Engineering Team").scope_type == "engineering"
    broad = detector.detect(title="Open Roles", description="Company is hiring several positions")
    assert broad.scope_type == "all_roles"
    assert broad.broad_hiring is True
    specific = detector.detect(title="Founding Backend Engineer")
    assert specific.scope_type == "specific_role"
    assert specific.specific_role is True
    assert detector.detect(title="Lago").scope_type == "unknown"

