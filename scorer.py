from typing import Dict, List, Optional


def score_risk(signals: Dict) -> Dict:
    risk_points = 0
    infra_penalty_points = 0
    content_penalty_points = 0
    findings: List[Dict[str, Optional[str]]] = []
    breakdown: List[Dict[str, str | int]] = []
    detected_signals: List[str] = []
    score = 64
    # Hard content downside cap to prevent over-sensitive swings.
    max_content_penalty = 12

    email_type = signals.get("email_type", "cold outreach")
    mode = signals.get("analysis_mode", "content")
    full_mode = mode == "full"
    auth_verifiable = bool(signals.get("auth_verifiable", False))

    email_type_confidence = 72
    if email_type == "cold outreach" and signals.get("automation_level") == "high":
        email_type_confidence = 85
    elif email_type == "transactional" and signals.get("is_no_reply_sender"):
        email_type_confidence = 88
    elif email_type == "marketing/newsletter" and signals.get("email_type_reason"):
        email_type_confidence = 78

    mode_label = "Full Deliverability Check" if full_mode else "Content Only"
    mode_note = (
        "Includes content + domain checks (SPF, DKIM, DMARC, alignment)."
        if full_mode
        else "Based on message content only. Domain infrastructure checks are not applied."
    )

    def add_penalty(points: int, label: str, reason: str, category: str = "content"):
        nonlocal risk_points, score, infra_penalty_points, content_penalty_points
        if points <= 0:
            return

        if category == "content":
            remaining = max_content_penalty - content_penalty_points
            if remaining <= 0:
                return
            points = min(points, remaining)
            content_penalty_points += points

        risk_points += points
        if category == "infra":
            infra_penalty_points += points
        score -= points
        breakdown.append({"label": label, "points": -points, "reason": reason})

    def add_boost(points: int, label: str, reason: str):
        nonlocal score
        score += points
        breakdown.append({"label": label, "points": points, "reason": reason})

    # Classification context
    findings.append(
        {
            "severity": "low",
            "title": f"Analysis mode: {mode_label}",
            "issue": mode_note,
            "impact": "Use the same mode across tests to compare scores fairly.",
            "fix": None,
        }
    )

    # Content signals
    spam_terms = signals.get("spam_terms") or []
    cta_phrases = signals.get("cta_phrases") or []
    aggressive_terms = signals.get("aggressive_tone_terms") or []
    link_count = int(signals.get("link_count", 0))
    confidence_killers = signals.get("confidence_killers") or []
    body_word_count = int(signals.get("body_word_count", 0))

    has_personalization = any(
        marker in (signals.get("email_type_reason", "").lower())
        for marker in ["noticed", "saw your", "about your", "personali"]
    )

    # Positive signals first: this improves score spread so good emails can actually score high.
    if has_personalization:
        add_boost(8, "Personalization detected", "Recipient-specific context detected")
        detected_signals.append("• Personalization detected")

    # Keep structure scoring mode-agnostic: base it on body quality only.
    # This avoids paste/manual drift caused by subject parsing differences.
    structure_score = 0
    if 20 <= body_word_count <= 320:
        structure_score += 5
    if 50 <= body_word_count <= 320:
        structure_score += 5
    if structure_score:
        add_boost(structure_score, "Clear structure", "Subject/body structure quality detected")

    if not spam_terms:
        add_boost(8, "Clean content", "Copy avoids common trigger phrases")

    if not aggressive_terms:
        add_boost(6, "Neutral tone", "No urgency pressure terms detected")

    if email_type in ("informational/system", "transactional"):
        add_boost(8, "Informational trust profile", "Message style looks informational over promotional")

    language_penalty = 0
    targeting_penalty = 0
    structure_penalty = 0
    friction_penalty = 0

    if email_type == "cold outreach" and not has_personalization:
        targeting_penalty += 8
        detected_signals.append("• No personalization detected (looks like bulk email)")
        findings.append(
            {
                "severity": "high",
                "title": "No personalization detected",
                "issue": "This message reads like a template, not a person-to-person email.",
                "impact": "Template-style outreach is downranked by inbox providers.",
                "fix": "Add recipient-specific context such as company detail, recent post, or role-specific pain.",
            }
        )

    if spam_terms:
        promo_penalty = min(8, len(spam_terms) * 4)
        language_penalty += promo_penalty
        detected_signals.append(f"• {len(spam_terms)} promotional phrase(s) ({', '.join(spam_terms[:2])})")

    normalized_cta = {p.strip().lower() for p in cta_phrases}
    non_overlap_urgency = [t for t in aggressive_terms if t.strip().lower() not in normalized_cta]

    cta_penalty = 0
    urgency_penalty = 0
    if cta_phrases:
        cta_penalty = min(10, 6 + max(0, len(cta_phrases) - 1) * 2)
        detected_signals.append(f"• CTA phrases detected ({', '.join(cta_phrases[:2])})")

    if non_overlap_urgency:
        urgency_penalty = min(10, len(non_overlap_urgency) * 6)
        detected_signals.append("• Uses urgency language (can trigger spam filters)")
        findings.append(
            {
                "severity": "high",
                "title": "Urgency language detected",
                "issue": "Pressure words can make this look promotional or suspicious.",
                "impact": "Urgency-heavy language increases filtering risk.",
                "fix": "Replace urgency words with clear, neutral timing and a calm CTA.",
            }
        )

    pressure_penalty = max(cta_penalty, urgency_penalty)
    pressure_reason = ""
    if pressure_penalty:
        reason_parts: List[str] = []
        if cta_phrases:
            reason_parts.append(f"CTA: {', '.join(cta_phrases[:2])}")
        if non_overlap_urgency:
            reason_parts.append(f"Urgency: {', '.join(non_overlap_urgency[:2])}")
        language_penalty += pressure_penalty
        pressure_reason = " | ".join(reason_parts)

    if signals.get("too_many_links", False):
        friction_penalty += 8
        detected_signals.append(f"• {link_count} links detected")
    elif link_count >= 2:
        friction_penalty += 5
        detected_signals.append(f"• {link_count} links detected")
    elif link_count == 1:
        add_boost(2, "Single link", "Focused call-to-action pattern")
        detected_signals.append("• 1 link detected")
    else:
        detected_signals.append("• 0 links detected")

    if signals.get("excessive_caps", False):
        structure_penalty += 4

    if signals.get("short_generic_email", False):
        structure_penalty += 5
        findings.append(
            {
                "severity": "medium",
                "title": "Generic call-to-action detected",
                "issue": "Your ask sounds broad and reusable across many recipients.",
                "impact": "Generic CTA patterns reduce trust and raise spam risk.",
                "fix": "Use one concrete ask tied to recipient context.",
            }
        )

    if confidence_killers:
        language_penalty += min(4, len(confidence_killers) * 2)

    opener_type = signals.get("opener_type")
    if email_type == "cold outreach" and opener_type in ("generic", "pattern-based"):
        targeting_penalty += 4

    intent_type = signals.get("intent_type")
    if email_type == "cold outreach" and intent_type in ("no-cta", "vague"):
        targeting_penalty += 4

    if signals.get("tracking_style_links", False):
        friction_penalty += 3

    # Group normalization to avoid overlap double counting.
    language_penalty = min(8, language_penalty)
    targeting_penalty = min(8, targeting_penalty)
    structure_penalty = min(6, structure_penalty)
    friction_penalty = min(8, friction_penalty)

    if language_penalty > 0:
        add_penalty(
            language_penalty,
            "Language pressure",
            pressure_reason or "Promotional or urgency-heavy phrasing detected",
            category="content",
        )
    if targeting_penalty > 0:
        add_penalty(
            targeting_penalty,
            "Targeting clarity risk",
            "Personalization/opener/CTA clarity signals indicate template-like outreach",
            category="content",
        )
    if structure_penalty > 0:
        add_penalty(
            structure_penalty,
            "Structure risk",
            "Formatting pattern resembles generic outreach",
            category="content",
        )
    if friction_penalty > 0:
        add_penalty(
            friction_penalty,
            "Friction risk",
            "Links/tracking footprint increases promotional profile",
            category="content",
        )

    # Profile adjustments (light-touch)
    if email_type == "transactional":
        add_boost(6, "Transactional profile", "Legitimate notification pattern")
    elif email_type == "marketing/newsletter":
        add_boost(3, "Newsletter profile", "Broadcast pattern recognized")
    elif email_type == "informational/system":
        add_boost(5, "Informational profile", "Announcement/system style recognized")

    # Infra checks only in full mode
    if full_mode:
        if auth_verifiable:
            findings.append(
                {
                    "severity": "low",
                    "title": "✅ Domain-level checks included",
                    "issue": "This score includes SPF, DKIM, DMARC, blacklist and alignment checks.",
                    "impact": "Scores can be lower than content-only mode when domain setup is weak.",
                    "fix": None,
                }
            )
        else:
            add_penalty(2, "Verification incomplete", "Full mode requested without enough verifiable domain/header evidence", category="infra")
            findings.append(
                {
                    "severity": "low",
                    "title": "⚠️ Full mode requested but headers/domain were incomplete",
                    "issue": "Domain checks were limited by missing verifiable header/domain data.",
                    "impact": "Paste complete headers and a valid domain for strict full-mode validation.",
                    "fix": None,
                }
            )

        blacklist_status = signals.get("blacklist_status", {})
        if blacklist_status.get("blacklisted", False):
            lists = ", ".join(blacklist_status.get("lists", []))
            add_penalty(16, "Domain blacklist status", f"Listed on {lists}", category="infra")
            detected_signals.append(f"• Domain listed on blacklist(s): {lists}")
        elif blacklist_status.get("status") == "unknown":
            detected_signals.append("• Blacklist check skipped (network-limited)")
        else:
            detected_signals.append("• Blacklist: not detected")

        spf_status = signals.get("spf_status", "missing")
        dkim_status = signals.get("dkim_status", "missing")
        dmarc_status = signals.get("dmarc_status", "missing")

        if spf_status == "missing":
            add_penalty(8, "SPF missing", f"SPF record not found on {signals.get('spf_checked_domain', 'domain')}", category="infra")
            detected_signals.append("• SPF missing")
        elif spf_status == "unknown":
            detected_signals.append("• SPF lookup unavailable")
        else:
            detected_signals.append("• SPF found")

        if dkim_status == "missing":
            add_penalty(6, "DKIM record missing", f"Selector record not found on {signals.get('dkim_checked_domain', 'domain')}", category="infra")
            detected_signals.append("• DKIM record missing")
        elif dkim_status == "not_verifiable":
            add_penalty(2, "DKIM not verifiable", "Signed headers/selector were not available for strict DKIM validation", category="infra")
            detected_signals.append("• DKIM not verifiable (requires signed headers)")
        elif dkim_status == "unknown":
            detected_signals.append("• DKIM lookup unavailable")
        else:
            detected_signals.append("• DKIM found")

        if not signals.get("spf_aligned", False):
            add_penalty(10, "From alignment mismatch", "From domain does not align with SPF domain", category="infra")
            detected_signals.append("• SPF alignment failed")

        if dmarc_status == "missing":
            add_penalty(6, "DMARC missing", f"DMARC policy not found on {signals.get('dmarc_checked_domain', 'domain')}", category="infra")
            detected_signals.append("• DMARC missing")
        elif dmarc_status == "unknown":
            detected_signals.append("• DMARC lookup unavailable")
        else:
            detected_signals.append("• DMARC found")
    else:
        detected_signals.append("• Domain-level checks skipped (Content Only mode)")

    content_score = max(35, min(95, score + infra_penalty_points))

    if content_score >= 80 and infra_penalty_points > 0:
        relief = min(6, max(1, round(infra_penalty_points * 0.25)))
        score += relief
        breakdown.append({
            "label": "High-quality content relief",
            "points": relief,
            "reason": "Strong content softens infrastructure drag in heuristic scoring",
        })

    score = max(35, min(95, score))

    # Ensure infra penalties are visible in full mode even near score ceiling.
    if full_mode and infra_penalty_points > 0:
        score = min(score, 95 - min(6, infra_penalty_points))

    if score >= 80:
        risk_band = "Likely Inbox"
        risk_pill_style = "low"
    elif score >= 60:
        risk_band = "⚠️ May hit Promotions/Spam"
        risk_pill_style = "medium"
    else:
        risk_band = "❌ Likely Spam"
        risk_pill_style = "high"

    spf_status = signals.get("spf_status", "not_checked")
    dkim_status = signals.get("dkim_status", "not_checked")
    dmarc_status = signals.get("dmarc_status", "not_checked")
    spf_aligned = bool(signals.get("spf_aligned", False))
    blacklist_status = signals.get("blacklist_status", {})
    blacklisted = bool(blacklist_status.get("blacklisted", False))

    if not full_mode:
        deliverability_confidence = "medium"
        confidence_note = "Content-only mode: sender authentication confidence is not fully verified."
    else:
        if blacklisted or spf_status == "missing" or not spf_aligned:
            deliverability_confidence = "low"
            confidence_note = "Authentication or sender reputation has high uncertainty/risk."
        elif dkim_status in ("missing", "not_verifiable") or dmarc_status in ("missing", "unknown"):
            deliverability_confidence = "medium"
            confidence_note = "Content looks strong, but authentication verification is partial."
        elif spf_status == "found" and dkim_status == "found" and dmarc_status == "found":
            deliverability_confidence = "high"
            confidence_note = "Authentication checks are complete and aligned."
        else:
            deliverability_confidence = "medium"
            confidence_note = "Some infrastructure checks are inconclusive."

    issues: List[Dict[str, object]] = []
    has_list_unsubscribe_marker = bool(signals.get("has_list_unsubscribe_marker", False))
    tracking_style_links = bool(signals.get("tracking_style_links", False))
    too_many_links = bool(signals.get("too_many_links", False))

    def impact_value(issue: Dict[str, object]) -> float:
        value = issue.get("impact", 0.0)
        if isinstance(value, (int, float)):
            return float(value)
        return 0.0

    def add_issue(
        issue_type: str,
        title: str,
        impact: float,
        action: str,
        why: str,
        providers: List[str] | None = None,
    ):
        issues.append(
            {
                "type": issue_type,
                "title": title,
                "impact": impact,
                "action": action,
                "why": why,
                "providers": providers or ["all"],
            }
        )

    if spam_terms:
        add_issue(
            "spam_phrases",
            "Promotional phrasing detected",
            0.35,
            "Replace promotional terms with neutral, specific wording.",
            f"Found trigger phrases: {', '.join(spam_terms[:3])}. These are frequently associated with promotional filtering.",
            ["gmail", "yahoo"],
        )

    if cta_phrases or non_overlap_urgency:
        add_issue(
            "aggressive_cta",
            "CTA pressure is high",
            0.3,
            "Use one low-pressure CTA and remove urgency wording.",
            "Urgency-heavy CTA patterns are often treated as campaign-style mail.",
            ["gmail", "yahoo", "outlook"],
        )

    if too_many_links or link_count >= 2 or tracking_style_links:
        add_issue(
            "link_density",
            "Link footprint is high",
            0.4,
            "Limit to one clean link and remove heavy tracking parameters.",
            "High link density/tracking parameters increase promotional classification risk.",
            ["gmail", "yahoo", "outlook"],
        )

    if tracking_style_links:
        add_issue(
            "tracking_link_reputation",
            "Tracking-style URL pattern",
            0.3,
            "Use direct destination URLs without redirect-style tracking params.",
            "Tracking and redirect-style URLs reduce trust with provider filters.",
            ["gmail"],
        )

    if email_type in ("marketing/newsletter", "cold outreach") and link_count >= 1 and not has_list_unsubscribe_marker:
        add_issue(
            "missing_list_unsubscribe",
            "List-Unsubscribe signal missing",
            0.55,
            "Add visible unsubscribe/manage-preferences controls for campaign-style mail.",
            "Outlook is stricter on list-unsubscribe signals for non-transactional sends.",
            ["outlook"],
        )

    if full_mode:
        if blacklisted:
            add_issue(
                "blacklisted_domain",
                "Domain appears on blacklist",
                1.0,
                "Resolve blacklist listings and warm reputation before sending campaigns.",
                "Mailbox providers strongly penalize listed sender domains.",
                ["gmail", "yahoo", "outlook"],
            )

        if spf_status == "missing":
            add_issue(
                "spf_missing",
                "SPF is missing",
                0.9,
                "Publish SPF and include all approved sending hosts.",
                "Without SPF, providers cannot validate sender authorization.",
                ["gmail", "yahoo", "outlook"],
            )
        elif spf_status == "found" and not spf_aligned:
            add_issue(
                "spf_misaligned",
                "SPF found but not aligned",
                0.85,
                "Align From domain with the SPF-authenticated envelope domain.",
                "Alignment failures reduce domain trust even when SPF exists.",
                ["gmail", "yahoo", "outlook"],
            )

        if dkim_status == "missing":
            add_issue(
                "dkim_missing",
                "DKIM signing missing",
                0.8,
                "Enable DKIM signing at your sender (ESP/mail provider).",
                "Missing DKIM weakens cryptographic sender authenticity checks.",
                ["gmail", "yahoo", "outlook"],
            )
        elif dkim_status == "not_verifiable":
            add_issue(
                "dkim_not_verifiable",
                "DKIM cannot be fully verified",
                0.45,
                "Send with full signed headers or verify selector configuration in your ESP.",
                "Providers cannot fully confirm DKIM authenticity from this input.",
                ["gmail", "yahoo", "outlook"],
            )

        if dmarc_status == "missing":
            add_issue(
                "dmarc_missing",
                "DMARC policy missing",
                0.7,
                "Publish DMARC policy (start with p=none, then enforce as reputation stabilizes).",
                "DMARC provides policy-level alignment and spoofing protection signals.",
                ["yahoo", "outlook"],
            )

    unique_fixes = {}
    for item in sorted(issues, key=impact_value, reverse=True):
        key = item["type"]
        if key not in unique_fixes:
            unique_fixes[key] = item
    top_fixes = list(unique_fixes.values())[:3]

    if not top_fixes:
        top_fixes = [
            {
                "type": "improve_personalization",
                "title": "Optional improvement: add personalization",
                "impact": 0.15,
                "action": "Reference recipient context (role/company/recent event) in opener.",
                "why": "Context-specific intros often improve trust and reply likelihood.",
                "providers": ["all"],
            }
        ]

    provider_results: Dict[str, Dict[str, object]] = {}
    provider_list = ["gmail", "outlook", "yahoo"]
    provider_base_score = content_score if not full_mode else score

    for provider in provider_list:
        provider_issues: List[Dict[str, object]] = []
        for issue in issues:
            providers = issue.get("providers", ["all"])
            if isinstance(providers, list) and (provider in providers or "all" in providers):
                provider_issues.append(issue)

        provider_penalty = sum(int(round(impact_value(issue) * 10)) for issue in provider_issues)
        provider_score = max(35, min(95, provider_base_score - provider_penalty))

        if provider_score >= 80:
            provider_status = "likely_inbox"
        elif provider_score >= 60:
            provider_status = "at_risk"
        else:
            provider_status = "high_risk"

        if provider_issues:
            best_issue = max(provider_issues, key=impact_value)
            provider_top_issue = str(best_issue.get("title", "No major provider-specific issue"))
        else:
            provider_top_issue = "No major provider-specific issue"
        provider_results[provider] = {
            "score": provider_score,
            "status": provider_status,
            "top_issue": provider_top_issue,
        }

    return {
        "score": score,
        "risk_band": risk_band,
        "risk_pill_style": risk_pill_style,
        "email_type": email_type,
        "email_type_confidence": email_type_confidence,
        "analysis_mode": mode,
        "analysis_mode_label": mode_label,
        "analysis_mode_note": mode_note,
        "capability_note": "Based on content and optional domain checks only. No real inbox placement testing is performed.",
        "infra_included": full_mode,
        "content_score": content_score,
        "infra_impact": -infra_penalty_points,
        "final_score": score,
        "deliverability_confidence": deliverability_confidence,
        "confidence_note": confidence_note,
        "top_fixes": top_fixes,
        "provider_results": provider_results,
        "risk_points": risk_points,
        "breakdown": breakdown,
        "findings": findings,
        "detected_signals": detected_signals,
    }
