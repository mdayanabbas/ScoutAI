from app.enrichment.domain_extractor import DomainProposal
from app.enrichment.proposal_ranker import (
    rank_domain_proposals,
    select_resolvable_proposal,
)


def test_business_email_domain_is_high_confidence():
    ranked = rank_domain_proposals(
        [
            DomainProposal(
                value="getdexter.co",
                domain="getdexter.co",
                source="raw_payload.text",
                resolver="business_email_domain",
                reason="business email",
            )
        ]
    )

    assert ranked[0].confidence == 0.9


def test_conflicting_domains_are_ambiguous():
    ranked = rank_domain_proposals(
        [
            DomainProposal("https://a.example", "a.example", "raw_description", "description_url", "url"),
            DomainProposal("https://b.example", "b.example", "raw_description", "description_url", "url"),
        ]
    )

    selected, reason = select_resolvable_proposal(ranked)

    assert selected is None
    assert reason == "ambiguous_domain_proposals"
