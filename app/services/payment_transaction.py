from app.models.payment_transaction import PaymentTransaction
from app.repositories.payment_transaction import PaymentTransactionRepository
from app.schemas.payment_transaction import PaymentTransactionCreate
from app.services.base import BaseService


class PaymentTransactionService(BaseService[PaymentTransaction]):
    repo: PaymentTransactionRepository  # type: ignore[assignment]

    def __init__(self, repo: PaymentTransactionRepository) -> None:
        super().__init__(repo, domain_name="payment_transaction")

    def create_transaction(self, data: PaymentTransactionCreate) -> PaymentTransaction:
        existing = self.repo.get_by_channel_transaction_id(data.channel_transaction_id)
        if existing is not None:
            self.logger.info(
                "payment_transaction.create_idempotent",
                extra={"transaction_id": existing.id, "channel_transaction_id": data.channel_transaction_id},
            )
            return existing

        txn = PaymentTransaction(
            payment_attempt_id=data.payment_attempt_id,
            order_id=data.order_id,
            channel=data.channel,
            amount=data.amount,
            currency=data.currency,
            channel_transaction_id=data.channel_transaction_id,
            raw_callback_data=data.raw_callback_data,
            status="confirmed",
        )
        created = self.repo.create(txn)
        self.logger.info(
            "payment_transaction.created",
            extra={
                "transaction_id": created.id,
                "payment_attempt_id": created.payment_attempt_id,
                "order_id": created.order_id,
                "channel_transaction_id": created.channel_transaction_id,
            },
        )
        return created

    def get_transaction(self, transaction_id: int) -> PaymentTransaction | None:
        return self.get(transaction_id)

    def list_by_attempt(self, payment_attempt_id: int) -> list[PaymentTransaction]:
        results = self.repo.get_by_payment_attempt_id(payment_attempt_id)
        self.logger.info(
            "payment_transaction.listed_by_attempt",
            extra={"payment_attempt_id": payment_attempt_id, "count": len(results)},
        )
        return results

    def list_by_order(self, order_id: int) -> list[PaymentTransaction]:
        results = self.repo.get_by_order_id(order_id)
        self.logger.info(
            "payment_transaction.listed_by_order",
            extra={"order_id": order_id, "count": len(results)},
        )
        return results

    def list_filtered(
        self,
        *,
        payment_attempt_id: int | None = None,
        order_id: int | None = None,
        channel: str | None = None,
        status: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[PaymentTransaction]:
        results = self.repo.list_filtered(
            payment_attempt_id=payment_attempt_id,
            order_id=order_id,
            channel=channel,
            status=status,
            limit=limit,
            offset=offset,
        )
        self.logger.info(
            "payment_transaction.listed_filtered",
            extra={
                "count": len(results),
                "filters": {
                    "payment_attempt_id": payment_attempt_id,
                    "order_id": order_id,
                    "channel": channel,
                    "status": status,
                },
            },
        )
        return results
