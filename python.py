import asyncio
import aiohttp
import time

class RateLimitedAPIClient:
    def __init__(self, base_url, rate_limit=5, period=1):
        self.base_url = base_url
        self.semaphore = asyncio.Semaphore(rate_limit)
        self.period = period
        self.request_times = []
        self.session = aiohttp.ClientSession()

    async def _throttle(self):
        now = time.time()
        self.request_times = [t for t in self.request_times if now - t < self.period]

        if len(self.request_times) >= self.semaphore._value:
            wait_time = self.period - (now - self.request_times[0])
            await asyncio.sleep(wait_time)

        self.request_times.append(time.time())

    async def fetch(self, endpoint, params=None):
        async with self.semaphore:
            await self._throttle()
            url = f"{self.base_url}{endpoint}"
            try:
                async with self.session.get(url, params=params) as response:
                    if response.status == 429:  # Rate limit exceeded
                        retry_after = int(response.headers.get("Retry-After", 1))
                        await asyncio.sleep(retry_after)
                        return await self.fetch(endpoint, params)  # Retry request
                    
                    response.raise_for_status()
                    return await response.json()
            except aiohttp.ClientError as e:
                print(f"Request failed: {e}")
                return None

    async def close(self):
        await self.session.close()

async def main():
    client = RateLimitedAPIClient(base_url="https://jsonplaceholder.typicode.com", rate_limit=5, period=1)
    
    tasks = [client.fetch("/todos/1") for _ in range(10)]
    results = await asyncio.gather(*tasks)

    await client.close()
    print(results)  # Print API responses

asyncio.run(main())

