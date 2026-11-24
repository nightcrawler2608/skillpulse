import pytest

from skillpulse.nlp.extractor import DictionaryExtractor, HybridExtractor, Match, job_text
from skillpulse.nlp.taxonomy import default_skills, load_skills

ex = DictionaryExtractor()


def test_taxonomy_loads_and_is_big_enough():
    skills = load_skills()
    assert len(skills) >= 200
    assert len({s.name for s in skills}) == len(skills)


@pytest.mark.parametrize("text, expected", [
    ("Strong SQL and Power BI skills", {"SQL", "Power BI"}),
    ("Experience with MS Excel, VLOOKUP and pivot tables",
     {"Microsoft Excel", "VLOOKUP", "Pivot Tables"}),
    ("Knowledge of C/C++ and C#", {"C", "C++", "C#"}),
    ("Hands-on PySpark and Airflow", {"Apache Spark", "Apache Airflow"}),
    ("Python-based ETL pipelines", {"Python", "ETL"}),
    ("Docker,Kubernetes(k8s)", {"Docker", "Kubernetes"}),
])
def test_finds_expected_skills(text, expected):
    assert expected <= ex.extract(text)


@pytest.mark.parametrize("text, not_expected", [
    ("Must know JavaScript", "Java"),       # Java is not inside JavaScript
    ("MySQL database admin", "SQL"),        # SQL is not inside MySQL
    ("C++ developer", "C"),                 # C is not inside C++
    ("You will excel in a fast-paced team", "Microsoft Excel"),  # verb, lowercase
    ("ideas that spark creativity", "Apache Spark"),             # lowercase spark
    ("Grade C or above", "C"),
    ("Full time R-71763 Who we are", "R"),                       # job reference code
    ("helping clients on their cloud and AI journeys", "Artificial Intelligence"),
    ("Go to market strategy", "Go"),
    ("Accounts reporting to the CFO", "R"),
])
def test_avoids_false_matches(text, not_expected):
    assert not_expected not in ex.extract(text)


@pytest.mark.parametrize("text, not_expected", [
    ("Our close collaboration worldwide", "Teamwork"),        # culture blurb noun
    ("customers can be more agile, efficient", "Agile"),     # adjective
    ("technology leadership services", "Leadership"),
    ("Atlas provides solutions across Oracle", "Oracle Database"),  # company name
    ("calling, messaging and other communication channels", "Communication"),
    ("Go-to-market strategy", "Go"),
])
def test_blurb_words_do_not_count(text, not_expected):
    assert not_expected not in ex.extract(text)


@pytest.mark.parametrize("text, expected", [
    ("You will collaborate closely with product teams", "Teamwork"),
    ("Lead and mentor junior engineers", "Leadership"),
    ("Agile methodology and sprint planning", "Agile"),
    ("Build services in Go, on AWS", "Go"),
    ("cloud-native architectures", "Cloud Computing"),
])
def test_new_phrasings_found(text, expected):
    assert expected in ex.extract(text)


def test_title_only_rules():
    # "AI" in the title counts; the same word in the body does not
    assert "Artificial Intelligence" in ex.extract("We build things.", title="AI Platform Engineer")
    assert "Artificial Intelligence" not in ex.extract("Our AI journey", title="Java Developer")
    # Gen AI titles are Generative AI, not plain AI
    assert "Artificial Intelligence" not in ex.extract("", title="Video Gen AI Engineer")
    assert "Cybersecurity" in ex.extract("", title="Security Platform Engineer")


def test_case_sensitive_forms_still_match():
    assert {"R", "Microsoft Excel", "Apache Spark"} <= ex.extract("Use R, Excel and Spark")


def test_multiword_alias_across_extra_spaces():
    assert "Power BI" in ex.extract("Power   BI dashboards")


def test_match_reports_evidence():
    m = {x.skill: x for x in ex.matches("Advanced Excel required")}
    assert m["Microsoft Excel"].alias.lower() == "advanced excel"


def test_empty_text():
    assert ex.extract(None) == set()
    assert ex.extract("") == set()


def test_job_text_joins_title_and_description():
    assert job_text("Data Analyst", None) == "Data Analyst"
    assert job_text("A", "B") == "A . B"


def test_hybrid_only_adds_new_skills():
    class FakeEmbedding:
        def matches(self, text):
            return [Match("SQL", "sql", "embedding"), Match("Tableau", "viz tool", "embedding")]
    h = HybridExtractor(DictionaryExtractor(default_skills()), FakeEmbedding())
    by_skill = {m.skill: m.method for m in h.matches("SQL")}
    assert by_skill == {"SQL": "dictionary", "Tableau": "embedding"}
