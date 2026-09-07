from pydantic import BaseModel, ConfigDict, Field

PAYMENT_METHOD_ID_PATTERN = r"^pm_[A-Za-z0-9_]+$"


class CheckoutSessionResponse(BaseModel):
    message: str
    checkout_url: str = Field(serialization_alias="checkoutUrl")
    session_id: str = Field(serialization_alias="sessionId")


class StripeWebhookResponse(BaseModel):
    message: str
    received: bool = True


class PaymentConfigResponse(BaseModel):
    publishable_key: str = Field(serialization_alias="publishableKey")


class SetupIntentResponse(BaseModel):
    message: str
    client_secret: str = Field(serialization_alias="clientSecret")


class SavedCardRead(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: str
    brand: str
    last4: str
    exp_month: int = Field(serialization_alias="expMonth")
    exp_year: int = Field(serialization_alias="expYear")
    type: str = "card"


class SavedCardListResponse(BaseModel):
    message: str
    data: list[SavedCardRead]


class PayOrderRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    payment_method_id: str = Field(
        ...,
        alias="paymentMethodId",
        min_length=6,
        pattern=PAYMENT_METHOD_ID_PATTERN,
        examples=["pm_1ExamplePaymentMethod"],
    )
