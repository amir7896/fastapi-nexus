from pydantic import BaseModel, Field


class CheckoutSessionResponse(BaseModel):
    message: str
    checkout_url: str = Field(serialization_alias="checkoutUrl")
    session_id: str = Field(serialization_alias="sessionId")


class StripeWebhookResponse(BaseModel):
    message: str
    received: bool = True
