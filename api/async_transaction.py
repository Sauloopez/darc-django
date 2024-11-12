from django.db import transaction, DEFAULT_DB_ALIAS
from asgiref.sync import sync_to_async

class AsyncAtomicTransaction(transaction.Atomic):
    def __init__(self, using= None, savepoint= True, durable= False):
        super().__init__(using, savepoint, durable)
        return

    async def __aenter__(self):
            await sync_to_async(super().__enter__)()
            return self

    async def __aexit__(self, exc_type, exc_value, traceback):
        await sync_to_async(super().__exit__)(exc_type, exc_value, traceback)
        return
    pass

def async_atomic(using=None, savepoint=True, durable=False):
    """
    Asynchronus version of original decorator in django.db.transaction.atomic
    """
    if callable(using):
        return AsyncAtomicTransaction(DEFAULT_DB_ALIAS, savepoint, durable)(using)
    else:
        return AsyncAtomicTransaction(using, savepoint, durable)
