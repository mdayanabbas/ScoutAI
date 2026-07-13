from types import SimpleNamespace

from app.matching.remote_eligibility import RemoteEligibilityClassifier


def classify(**kwargs):
    job = SimpleNamespace(remote_type=kwargs.get("remote_type"), location=kwargs.get("location"), description=kwargs.get("description"), work_authorization=kwargs.get("work_authorization"), visa_sponsorship=kwargs.get("visa_sponsorship"))
    profile = SimpleNamespace(willing_to_relocate=False)
    return RemoteEligibilityClassifier().classify(job, profile).classification


def test_remote_eligibility_priority_cases():
    assert classify(remote_type="remote_worldwide") == "work_from_anywhere"
    assert classify(description="Work from anywhere in the world.") == "work_from_anywhere"
    assert classify(description="Remote in India.") == "remote_india_eligible"
    assert classify(description="Remote role for a global contractor.") == "remote_india_eligible"
    assert classify(remote_type="remote_country", description="Remote") == "remote_eligibility_unclear"
    assert classify(description="Remote, US only.") == "remote_country_restricted"
    assert classify(description="Canada only remote.") == "remote_country_restricted"
    assert classify(description="UK/EU only.") == "remote_region_restricted"
    assert classify(description="EMEA remote.") == "remote_region_restricted"
    assert classify(description="APAC including India.") == "remote_india_eligible"
    assert classify(remote_type="hybrid") == "hybrid"
    assert classify(remote_type="onsite") == "onsite"
    assert classify() == "unknown"


def test_authorization_restriction_overrides_generic_remote():
    result = RemoteEligibilityClassifier().classify(
        SimpleNamespace(remote_type="remote_worldwide", location="Remote", description="Remote worldwide.", work_authorization="US citizenship required.", visa_sponsorship=None),
        SimpleNamespace(willing_to_relocate=False),
    )

    assert result.classification == "remote_country_restricted"
    assert result.reason == "authorization_restriction"


def test_explicit_onsite_phrases_are_onsite():
    assert classify(location="Detroit", description="This role is full time, in person in Detroit.") == "onsite"
    assert classify(description="This role is not remote.") == "onsite"
    assert classify(description="Remote work is not available for this role.") == "onsite"


def test_optional_office_or_offsite_mentions_do_not_force_onsite():
    assert classify(description="Remote worldwide. Optional office visits are welcome.") == "work_from_anywhere"
    assert classify(description="Remote role with annual team meetups and company offsites.") == "remote_global_unspecified"
    assert classify(location="San Francisco", description="Build excellent systems.") == "unknown"
    assert classify(description="Build excellent systems.") == "unknown"
