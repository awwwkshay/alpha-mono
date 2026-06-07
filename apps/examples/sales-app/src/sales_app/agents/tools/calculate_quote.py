from __future__ import annotations

from typing import Literal, TypeAlias

from pydantic import BaseModel, Field

from clay_core import AgentTool, AppContext


BillingTerm = Literal["monthly", "annual"]


class CalculateQuoteInput(BaseModel):
    product_name: str
    seats: int = Field(ge=1)
    price_per_seat_usd: float = Field(ge=0)
    billing_term: BillingTerm = "annual"
    discount_percent: float = Field(default=0, ge=0, le=80)
    implementation_fee_usd: float = Field(default=0, ge=0)


class CalculateQuoteOutput(BaseModel):
    subtotal_usd: float
    discount_usd: float
    implementation_fee_usd: float
    total_first_term_usd: float
    monthly_equivalent_usd: float
    quote_summary: str


Input: TypeAlias = CalculateQuoteInput
Output: TypeAlias = CalculateQuoteOutput


async def _execute(inp: Input, ctx: AppContext) -> Output:
    _ = ctx
    multiplier = 12 if inp.billing_term == "annual" else 1
    subtotal = inp.seats * inp.price_per_seat_usd * multiplier
    discount = subtotal * (inp.discount_percent / 100)
    total = subtotal - discount + inp.implementation_fee_usd
    monthly_equivalent = total / 12 if inp.billing_term == "annual" else total

    summary = (
        f"{inp.product_name}: {inp.seats} seats at ${inp.price_per_seat_usd:,.2f}/seat "
        f"{inp.billing_term}, {inp.discount_percent:.1f}% discount, "
        f"first-term total ${total:,.2f}."
    )
    return Output(
        subtotal_usd=round(subtotal, 2),
        discount_usd=round(discount, 2),
        implementation_fee_usd=round(inp.implementation_fee_usd, 2),
        total_first_term_usd=round(total, 2),
        monthly_equivalent_usd=round(monthly_equivalent, 2),
        quote_summary=summary,
    )


calculate_quote_tool: AgentTool[CalculateQuoteInput, CalculateQuoteOutput] = AgentTool(
    name="Calculate Quote",
    description="Calculates a first-term sales quote with seats, billing term, discount, and fees.",
    input_schema=CalculateQuoteInput,
    output_schema=CalculateQuoteOutput,
    execute=_execute,
)

__all__ = ["calculate_quote_tool"]
