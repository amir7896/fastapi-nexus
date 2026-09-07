from fastapi import APIRouter, Request, status

from app.api.deps import CurrentUserDep, StripePaymentServiceDep
from app.schemas.payment import (
    PaymentConfigResponse,
    SavedCardListResponse,
    SetupIntentResponse,
    StripeWebhookResponse,
)

router = APIRouter(prefix="/payments", tags=["Payments"])


@router.get(
    "/config",
    response_model=PaymentConfigResponse,
    response_model_by_alias=True,
    summary="Return the Stripe publishable key for the in-app card form",
)
def payment_config(
    _: CurrentUserDep,
    stripe_payment_service: StripePaymentServiceDep,
) -> PaymentConfigResponse:
    return stripe_payment_service.payment_config()


@router.post(
    "/setup-intent",
    response_model=SetupIntentResponse,
    response_model_by_alias=True,
    summary="Create a SetupIntent so Stripe.js can collect a card",
)
def create_setup_intent(
    current_user: CurrentUserDep,
    stripe_payment_service: StripePaymentServiceDep,
) -> SetupIntentResponse:
    return stripe_payment_service.create_setup_intent(current_user)


@router.get(
    "/methods",
    response_model=SavedCardListResponse,
    response_model_by_alias=True,
    summary="List the current user's saved cards",
)
def list_payment_methods(
    current_user: CurrentUserDep,
    stripe_payment_service: StripePaymentServiceDep,
) -> SavedCardListResponse:
    return stripe_payment_service.list_saved_cards(current_user)


@router.delete(
    "/methods/{payment_method_id}",
    response_model=SavedCardListResponse,
    response_model_by_alias=True,
    status_code=status.HTTP_200_OK,
    summary="Detach a saved card from the current user",
)
def delete_payment_method(
    payment_method_id: str,
    current_user: CurrentUserDep,
    stripe_payment_service: StripePaymentServiceDep,
) -> SavedCardListResponse:
    return stripe_payment_service.detach_saved_card(current_user, payment_method_id)


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
