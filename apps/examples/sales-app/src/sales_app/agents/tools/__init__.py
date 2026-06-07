from sales_app.agents.tools.calculate_quote import (
    calculate_quote_tool as CALCULATE_QUOTE_TOOL,
)
from sales_app.agents.tools.draft_follow_up import (
    draft_follow_up_tool as DRAFT_FOLLOW_UP_TOOL,
)
from sales_app.agents.tools.plan_outreach import (
    plan_outreach_tool as PLAN_OUTREACH_TOOL,
)
from sales_app.agents.tools.qualify_lead import qualify_lead_tool as QUALIFY_LEAD_TOOL

TOOLS = {
    "calculate_quote": CALCULATE_QUOTE_TOOL,
    "draft_follow_up": DRAFT_FOLLOW_UP_TOOL,
    "plan_outreach": PLAN_OUTREACH_TOOL,
    "qualify_lead": QUALIFY_LEAD_TOOL,
}

__all__ = ["TOOLS"]
