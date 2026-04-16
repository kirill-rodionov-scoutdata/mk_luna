"""
Payment endpoints.

POST /api/v1/payments       → create payment (idempotent)
GET  /api/v1/payments/{id}  → get payment details
"""

import uuid

from dependency_injector.wiring import Provide, inject
from fastapi import APIRouter, Depends, Header, HTTPException, status

from app.api.dependencies import verify_api_key
from app.api.v1.schemas import CreatePaymentRequest, PaymentCreatedResponse, PaymentDetailResponse
from app.app_layer.services.payment_service import PaymentService
from app.container import Container
from app.domain.exceptions import PaymentNotFoundError

router = APIRouter(dependencies=[Depends(verify_api_key)])


@router.post(
    "",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=PaymentCreatedResponse,
    summary="Create a payment",
)
@inject
async def create_payment(
    body: CreatePaymentRequest,
    idempotency_key: str = Header(..., alias="Idempotency-Key"),
    payment_service: PaymentService = Depends(Provide[Container.payment_service]),
) -> PaymentCreatedResponse:
    payment = await payment_service.create_payment(
        idempotency_key=idempotency_key,
        amount=body.amount,
        currency=body.currency,
        description=body.description,
        metadata=body.metadata,
        webhook_url=str(body.webhook_url),
    )
    return PaymentCreatedResponse(
        payment_id=payment.id,
        status=payment.status,
        created_at=payment.created_at,
    )


@router.get(
    "/{payment_id}",
    response_model=PaymentDetailResponse,
    summary="Get payment details",
)
@inject
async def get_payment(
    payment_id: uuid.UUID,
    payment_service: PaymentService = Depends(Provide[Container.payment_service]),
) -> PaymentDetailResponse:
    try:
        payment = await payment_service.get_payment(payment_id)
    except PaymentNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))

    return PaymentDetailResponse(
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
