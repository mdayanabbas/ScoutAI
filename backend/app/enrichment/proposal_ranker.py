from dataclasses import dataclass

from app.enrichment.domain_extractor import (
    DomainProposal,
    is_allowed_company_domain,
)


@dataclass(frozen=True)
class RankedDomainProposal:
    proposal: DomainProposal
    confidence: float
    reason: str


def rank_domain_proposals(
    proposals: list[DomainProposal],
) -> list[RankedDomainProposal]:
    ranked: list[RankedDomainProposal] = []
    for proposal in proposals:
        if not is_allowed_company_domain(proposal.domain):
            continue
        confidence, reason = _score(proposal)
        if confidence > 0:
            ranked.append(RankedDomainProposal(proposal, confidence, reason))
    return sorted(ranked, key=lambda item: item.confidence, reverse=True)


def select_resolvable_proposal(
    ranked: list[RankedDomainProposal],
) -> tuple[RankedDomainProposal | None, str | None]:
    if not ranked:
        return None, "no_domain_proposals"
    domains = {item.proposal.domain for item in ranked}
    if len(domains) > 1:
        return None, "ambiguous_domain_proposals"
    return ranked[0], None


def _score(proposal: DomainProposal) -> tuple[float, str]:
    if proposal.resolver == "existing_url":
        return 1.0, "existing first-party URL"
    if proposal.resolver == "business_email_domain":
        return 0.9, "business email domain"
    if proposal.resolver == "evidence_url":
        return 0.85, "first-party URL in evidence"
    if proposal.source in {"raw_description", "normalized_description", "raw_payload.text"}:
        return 0.75, "URL in candidate description"
    return 0.7, "candidate source URL"
