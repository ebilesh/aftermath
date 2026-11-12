"""Replaceable verification boundary. Handlers must never write ledger credits."""
from dataclasses import dataclass
from typing import Protocol

@dataclass(frozen=True)
class VerifiedPayment:
    signature: str
    lamports: int
    evidence: str

class PaymentHandler(Protocol):
    def verify(self, order_id: str) -> VerifiedPayment: ...

class SimulatedPaymentHandler:
    """Synthetic chain input; the worker, SQL transactions and ledger are real."""
    def verify(self, order_id: str) -> VerifiedPayment:
        return VerifiedPayment('sim:'+order_id,25000000,
            'Simulated finalized transfer: recipient and 25000000 lamports match the order.')
