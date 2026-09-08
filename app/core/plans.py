from dataclasses import dataclass


@dataclass(frozen=True)
class Plan:
    id: str
    name: str
    seats: int
    products: int
    description: str


PLANS: dict[str, Plan] = {
    "free": Plan(
        id="free",
        name="Free",
        seats=3,
        products=20,
        description="One store, a small team, and a starter catalog.",
    ),
    "pro": Plan(
        id="pro",
        name="Pro",
        seats=10,
        products=200,
        description="More staff seats and a larger catalog.",
    ),
    "business": Plan(
        id="business",
        name="Business",
        seats=50,
        products=2000,
        description="For teams that sell at volume.",
    ),
}

DEFAULT_PLAN_ID = "free"


def get_plan(plan_id: str | None) -> Plan:
    if plan_id and plan_id in PLANS:
        return PLANS[plan_id]
    return PLANS[DEFAULT_PLAN_ID]
