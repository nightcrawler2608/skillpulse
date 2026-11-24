import numpy as np
import pytest

from skillpulse.matching.embedder import to_pgvector
from skillpulse.matching.recommender import fit_score, rescale_similarity, smoothed_overlap


def test_rescale_clips_to_0_1():
    assert rescale_similarity(0.0) == 0.0
    assert rescale_similarity(0.40) == pytest.approx(0.5)
    assert rescale_similarity(0.9) == 1.0


def test_fit_blends_meaning_and_smoothed_skills():
    fit, overlap = fit_score(0.40, {"SQL", "Python", "Tableau", "Excel"}, {"SQL", "Python"})
    assert overlap == 0.5
    assert fit == pytest.approx(0.5 * 0.5 + 0.5 * (2.5 / 5))


def test_smoothing_is_less_sure_about_short_lists():
    assert smoothed_overlap(1, 1) == pytest.approx(0.75)    # 1 of 1 is not "100%"
    assert smoothed_overlap(5, 5) == pytest.approx(5.5 / 6)
    assert smoothed_overlap(0, 0) == 0.5                    # no info -> neutral


def test_job_without_skills_gets_neutral_skill_part():
    fit, overlap = fit_score(0.65, set(), {"SQL"})
    assert overlap is None and fit == pytest.approx(0.75)


def test_more_matching_skills_ranks_higher():
    a, _ = fit_score(0.4, {"SQL", "Python"}, {"SQL", "Python"})
    b, _ = fit_score(0.4, {"SQL", "Python"}, {"SQL"})
    assert a > b


def test_pgvector_format():
    assert to_pgvector(np.array([0.5, -1.0])) == "[0.500000,-1.000000]"
