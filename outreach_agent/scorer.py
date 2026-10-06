from config import HOT_LEAD_SCORE, MIN_LEAD_SCORE

def score_lead(lead: dict) -> dict:
    score = 0
    reasons = []

    if not lead.get("website"):
        score += 3
        reasons.append("No website (+3)")
    else:
        reasons.append("Has website (0)")

    try:
        rating = float(lead.get("rating", 0))
        if 3.5 <= rating <= 4.3:
            score += 2
            reasons.append(f"Rating {rating} sweet spot (+2)")
        elif rating > 4.3:
            score += 1
            reasons.append(f"Rating {rating} high (+1)")
        elif rating > 0:
            reasons.append(f"Rating {rating} low (0)")
    except Exception:
        pass

    try:
        reviews = int(lead.get("reviews", 0))
        if 20 <= reviews <= 300:
            score += 2
            reasons.append(f"{reviews} reviews - ideal size (+2)")
        elif reviews > 300:
            score += 1
            reasons.append(f"{reviews} reviews - large business (+1)")
        elif reviews > 0:
            score += 1
            reasons.append(f"{reviews} reviews - small but exists (+1)")
        else:
            reasons.append("No reviews (0)")
    except Exception:
        pass

    if lead.get("phone"):
        score += 2
        reasons.append("Phone available (+2)")
    else:
        reasons.append("No phone (0)")

    if lead.get("address") and len(lead.get("address", "")) > 10:
        score += 1
        reasons.append("Address complete (+1)")

    score = min(score, 10)

    if score >= HOT_LEAD_SCORE:
        tier = "Hot"
    elif score >= MIN_LEAD_SCORE:
        tier = "Warm"
    else:
        tier = "Cold"

    lead["score"] = score
    lead["tier"] = tier
    lead["score_reasons"] = " | ".join(reasons)

    return lead

def score_all_leads(leads: list[dict]) -> list[dict]:
    scored = [score_lead(lead) for lead in leads]
    scored.sort(key=lambda x: x["score"], reverse=True)

    hot = len([l for l in scored if l["tier"] == "Hot"])
    warm = len([l for l in scored if l["tier"] == "Warm"])
    cold = len([l for l in scored if l["tier"] == "Cold"])

    print(f"\nScoring Complete:")
    print(f"   Hot leads:  {hot}")
    print(f"   Warm leads: {warm}")
    print(f"   Cold leads: {cold}")

    return scored

def filter_actionable_leads(leads: list[dict]) -> list[dict]:
    return [l for l in leads if l["score"] >= MIN_LEAD_SCORE]