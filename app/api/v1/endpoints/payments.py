from fastapi import APIRouter, Request

from app.api.deps import StripePaymentServiceDep
from app.schemas.payment import StripeWebhookResponse

router = APIRouter(prefix="/payments", tags=["Payments"])


@router.post(
    "/stripe/webhook",
    response_model=StripeWebhookResponse,
    summary="Stripe webhook endpoint",
)
async def stripe_webhook(
    request: Request,
    stripe_payment_service: StripePaymentServiceDep,
) -> StripeWebhookResponse:
    payload = await request.body()
    signature = request.headers.get("stripe-signature")
    return stripe_payment_service.handle_webhook(payload, signature)
