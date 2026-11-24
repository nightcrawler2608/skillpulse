from skillpulse.matching.stack import core_stack, stack_factor


def test_frameworks_imply_language():
    assert core_stack({"Django", "SQL", "REST APIs"}) == {"Django", "Python"}
    assert "JavaScript" in core_stack({"React"})


def test_mismatch_lowers_fit():
    assert stack_factor({"Java", "Spring Boot"}, {"Python", "Django"}) == 0.6


def test_overlap_or_missing_info_keeps_fit():
    assert stack_factor({"TypeScript", "Angular"}, {"React"}) == 1.0     # JavaScript family
    assert stack_factor({"Java"}, {"Excel", "SQL"}) == 1.0              # user lists no stack
    assert stack_factor({"Machine Learning"}, {"Python"}) == 1.0        # job lists no stack
