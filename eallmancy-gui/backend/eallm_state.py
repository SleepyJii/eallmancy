



import asyncio


class SharedState:
    def __init__(self, **kwargs):
        self.data = dict(**kwargs)
        self.lock = asyncio.Lock()

    async def get(self, key):
        async with self.lock:
            return self.data.get(key)

    async def update(self, **kwargs):
        async with self.lock:
            self.data.update(kwargs)

    async def items(self):
        async with self.lock:
            return dict(self.data).items()
        

