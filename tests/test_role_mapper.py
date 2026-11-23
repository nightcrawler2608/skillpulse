import pytest

from skillpulse.ingest.role_mapper import RoleMapper

mapper = RoleMapper()


@pytest.mark.parametrize("title, expected", [
    ("Jr. Data Analyst - Fresher (Remote)", "Data Analyst"),
    ("Senior Data Scientist", "Data Scientist"),
    ("Machine Learning Engineer II", "Machine Learning Engineer"),
    ("Big Data Engineer (Spark)", "Data Engineer"),
    ("Business Analyst - Banking", "Business Analyst"),
    ("SDE 1", "Software Engineer"),
    ("React Developer", "Frontend Developer"),
    ("Python Developer", "Backend Developer"),
    ("MERN Stack Developer", "Full Stack Developer"),
    ("Site Reliability Engineer", "DevOps / Cloud Engineer"),
    ("Power BI Technical Consultant", "Data Analyst"),
    ("Scrum Master", None),
    ("Accountant", None),
    ("Measurement Technician", None),   # 'sre' must not match inside a word
])
def test_role_mapping(title, expected):
    assert mapper.role_name(title) == expected


def test_role_id_uses_given_ids():
    m = RoleMapper(role_ids={"Data Analyst": 7})
    assert m.role_id("Data Analyst") == 7
    assert m.role_id("Accountant") is None
