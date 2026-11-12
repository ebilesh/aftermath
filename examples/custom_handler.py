"""Example merchant verifier adapter, backed by a fake chain in its tests."""
from backend.handlers import VerifiedPayment

class MerchantHandler:
    def __init__(self, lookup=None):
        # Replace this with your own read-only chain lookup. No ledger writes here.
        self.lookup=lookup or (lambda order: {'signature':'example:'+order,
            'recipient':'merchant-demo','lamports':25000000,'finalized':True,'err':None})
    def verify(self, order_id):
        tx=self.lookup(order_id)
        if tx is None: raise ValueError('Transaction unavailable; leave notification pending')
        if tx['err'] is not None or not tx['finalized']: raise ValueError('Payment not successful and finalized')
        if tx['recipient']!='merchant-demo' or tx['lamports']!=25000000: raise ValueError('Recipient or amount mismatch')
        return VerifiedPayment(tx['signature'],tx['lamports'],'Example handler verified matching merchant, amount, finality and execution status against fake chain data.')
