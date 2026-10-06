import uuid
from typing import Annotated

from dishka.integrations.fastapi import DishkaRoute, FromDishka
from fastapi import APIRouter, Depends, Header, status

from core.adapters.controllers.http.auth import require_api_key
from core.adapters.controllers.http.schema import (
    CreatePaymentRequest,
    CreatePaymentResponse,
    ErrorResponse,
    PaymentResponse,
)
from core.application.create_payment.dto import CreatePaymentDTO
from core.application.create_payment.usecases import CreatePayment
from core.application.get_payment import GetPayment

router = APIRouter(
    prefix='/api/v1/payments',
    tags=['payments'],
    route_class=DishkaRoute,
    dependencies=[Depends(require_api_key)],
    responses={401: {'model': ErrorResponse}},
)


@router.post(
    '',
    status_code=status.HTTP_202_ACCEPTED,
    response_model=CreatePaymentResponse,
    responses={409: {'model': ErrorResponse}},
)
async def create_payment(
    body: CreatePaymentRequest,
    usecase: FromDishka[CreatePayment],
    idempotency_key: Annotated[str, Header(min_length=1, max_length=255)],
) -> CreatePaymentResponse:
    payment = await usecase(
        CreatePaymentDTO(
            amount=body.amount,
            currency=body.currency,
            description=body.description,
            metadata=body.metadata,
            webhook_url=str(body.webhook_url),
            idempotency_key=idempotency_key,
        ),
    )
    return CreatePaymentResponse(payment_id=payment.id, status=payment.status, created_at=payment.created_at)


@router.get('/{payment_id}', response_model=PaymentResponse, responses={404: {'model': ErrorResponse}})
async def get_payment(payment_id: uuid.UUID, usecase: FromDishka[GetPayment]) -> PaymentResponse:
    payment = await usecase(payment_id)
    return PaymentResponse(
        payment_id=payment.id,
        amount=payment.amount,
        currency=payment.currency,
        description=payment.description,
        metadata=payment.metadata,
        status=payment.status,
        idempotency_key=payment.idempotency_key,
        webhook_url=payment.webhook_url,
        created_at=payment.created_at,
        processed_at=payment.processed_at,
    )
