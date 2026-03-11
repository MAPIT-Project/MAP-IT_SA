"""Imminent funding calls search with feasibility assessment."""

import logging
from datetime import date, datetime

logger = logging.getLogger(__name__)

__all__ = [
    "search_imminent_calls_with_warning_execute",
]


async def search_imminent_calls_with_warning_execute(query: str) -> str:
    """Search for calls with imminent deadlines AND provide realistic feasibility assessment.

    This function:
    1. Searches for calls closing within 7 days
    2. Provides a REALISTIC assessment that 1 week is NOT enough time
    3. Shows the calls but with strong warnings
    4. Suggests alternatives (next month, partner role only)

    Args:
        query: The user's query about imminent calls

    Returns:
        Formatted response with calls and feasibility warnings
    """
    # Search for open calls
    try:
        from ..local_call_search_service import LocalCallSearchService

        call_service = LocalCallSearchService()
        today = date.today()

        # Get all open calls
        results = call_service.search_calls(
            query="",  # No keyword filter - we want all calls
            num_results=50,  # Get more to filter
            include_closed=False,
        )

        calls = results.get("calls", [])

        # Filter to calls with deadlines within 7 days
        imminent_calls = []
        upcoming_calls = []  # Calls with deadline 7-30 days out

        for call in calls:
            deadline_str = call.get("deadline")
            if not deadline_str:
                continue

            try:
                # Parse deadline - handle different formats
                if isinstance(deadline_str, str):
                    # Try common formats
                    for fmt in ["%Y-%m-%d", "%d-%m-%Y", "%Y/%m/%d", "%d/%m/%Y"]:
                        try:
                            deadline_date = datetime.strptime(deadline_str, fmt).date()
                            break
                        except ValueError:
                            continue
                    else:
                        continue
                elif isinstance(deadline_str, date):
                    deadline_date = deadline_str
                else:
                    continue

                days_until = (deadline_date - today).days

                if 0 <= days_until <= 7:
                    call["days_until_deadline"] = days_until
                    imminent_calls.append(call)
                elif 7 < days_until <= 30:
                    call["days_until_deadline"] = days_until
                    upcoming_calls.append(call)

            except (ValueError, TypeError):
                continue

        # Sort by deadline (soonest first)
        imminent_calls.sort(key=lambda x: x.get("days_until_deadline", 999))
        upcoming_calls.sort(key=lambda x: x.get("days_until_deadline", 999))

    except Exception as e:
        logger.error(f"Error searching for imminent calls: {e}")
        imminent_calls = []
        upcoming_calls = []

    # Generate the response with realistic assessment
    response_parts = []

    # Start with the realistic assessment warning
    response_parts.append(
        """## ⚠️ Realistic Assessment: One Week is NOT Enough Time

I want to be honest with you: **one week is almost never enough time** to prepare a competitive EU funding proposal. Here's why:

| What You Need | Minimum Time Required |
|--------------|----------------------|
| **Consortium confirmation** | 1-2 weeks (partners need time to decide) |
| **Technical writing** | 2-4 weeks (Excellence, Impact, Implementation) |
| **Budget coordination** | 1-2 weeks (all partners must agree) |
| **Internal review** | 3-5 days (quality check before submission) |
| **Portal submission** | 1-2 days (technical setup, forms) |

**Typical total: 6-12 weeks** for a competitive proposal.

---
"""
    )

    # Show imminent calls if any
    if imminent_calls:
        response_parts.append(
            f"## 🔴 Calls Closing Within 7 Days ({len(imminent_calls)} found)\n\n"
        )
        response_parts.append(
            "**Important**: These calls are shown for awareness, but submitting a quality proposal is likely NOT feasible:\n\n"
        )

        for call in imminent_calls[:5]:  # Limit to 5
            call_id = call.get("topic_code", "Unknown")
            title = call.get("title", "Unknown Title")
            deadline = call.get("deadline", "Unknown")
            days = call.get("days_until_deadline", "?")
            budget = call.get("budget", "")
            url = call.get("url", "")

            response_parts.append(f"### {call_id}\n")
            response_parts.append(f"**{title}**\n")
            response_parts.append(
                f"- ⏰ Deadline: **{deadline}** ({days} days left) ❌ Too late for new application\n"
            )
            if budget:
                response_parts.append(f"- 💰 Budget: {budget}\n")
            if url:
                response_parts.append(f"- 🔗 [View on EU Portal]({url})\n")
            response_parts.append("\n")

        response_parts.append("---\n\n")

    else:
        response_parts.append("## Calls Closing This Week\n\n")
        response_parts.append(
            "**Good news**: There are no calls closing in the next 7 days, so you haven't missed anything urgent.\n\n"
        )
        response_parts.append("---\n\n")

    # Show upcoming calls (better alternatives)
    if upcoming_calls:
        response_parts.append(
            f"## ✅ Better Options: Calls Closing in 1-4 Weeks ({len(upcoming_calls[:5])} shown)\n\n"
        )
        response_parts.append(
            "These calls give you **more time** to prepare a quality proposal:\n\n"
        )

        for call in upcoming_calls[:5]:  # Limit to 5
            call_id = call.get("topic_code", "Unknown")
            title = call.get("title", "Unknown Title")
            deadline = call.get("deadline", "Unknown")
            days = call.get("days_until_deadline", "?")
            budget = call.get("budget", "")
            url = call.get("url", "")

            feasibility = (
                "🟡 Tight but possible with existing consortium"
                if days >= 14
                else "🟠 Very challenging"
            )

            response_parts.append(f"### {call_id}\n")
            response_parts.append(f"**{title}**\n")
            response_parts.append(
                f"- ⏰ Deadline: **{deadline}** ({days} days left) - {feasibility}\n"
            )
            if budget:
                response_parts.append(f"- 💰 Budget: {budget}\n")
            if url:
                response_parts.append(f"- 🔗 [View on EU Portal]({url})\n")
            response_parts.append("\n")

        response_parts.append("---\n\n")

    # Provide actionable alternatives
    response_parts.append(
        """## 🎯 What You Should Do Instead

### Option 1: Target the NEXT Cut-Off Date
Most Horizon Europe calls have **multiple cut-off dates** per year. Missing this week's deadline means you can target the next one with a stronger proposal.

📅 **Find next cut-offs**: [Funding & Tenders Portal](https://ec.europa.eu/info/funding-tenders/opportunities/portal/)

### Option 2: Join as a Partner (Not Coordinator)
If you really want to be involved in an imminent submission:
- Join an **existing consortium** as a partner
- They handle most of the coordination
- You contribute your expertise section only

🔍 **Find consortia looking for partners**: [Partner Search](https://ec.europa.eu/info/funding-tenders/opportunities/portal/screen/how-to-participate/partner-search)

### Option 3: Build for the Future
Use this time to:
1. **Identify your target call** for next round
2. **Build your consortium** now
3. **Start drafting early** - 3-6 months is ideal
4. **Contact your NCP** for guidance

📞 **National Contact Points**: [Find Your NCP](https://ec.europa.eu/info/funding-tenders/opportunities/portal/screen/support/ncp)

---

## ⚡ Reality Check

| If you submit this week... | Likely outcome |
|---------------------------|----------------|
| ❌ Rushed, incomplete proposal | Rejection (success rate drops to <5%) |
| ❌ No consortium agreements | Administratively ineligible |
| ❌ Poor quality writing | Low evaluation score |
| ❌ Budget not validated | Financial issues later |

| If you wait for next deadline... | Likely outcome |
|----------------------------------|----------------|
| ✅ Time to build strong consortium | Higher success rate |
| ✅ Quality technical content | Better evaluation scores |
| ✅ Proper partner commitments | Smooth project execution |
| ✅ Realistic budget planning | Financial security |

**The EU funding process rewards preparation, not speed.** A well-prepared proposal for the next deadline will always beat a rushed one for this week.

---

📞 **Need help planning?** Contact your [National Contact Point (NCP)](https://ec.europa.eu/info/funding-tenders/opportunities/portal/screen/support/ncp) - they provide FREE advice on proposal strategy and timing."""
    )

    return "".join(response_parts)
