from typing import Dict, List
from abc import ABC, abstractmethod

import logging, asyncio, aiohttp
import requests
from tqdm import tqdm

from src.models import ProxyConfig, VintedItemStatus


class BaseAvailabilityChecker(ABC):
    BASE_HEADERS = {
        "Accept": "application/json",
        "Accept-Language": "en-US,en;q=0.9",
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    }

    BASE_URL = "https://www.vinted.fr"
    BASE_API_URL = "https://www.vinted.fr/api/v2/items/{}/details"

    def __init__(self, proxy_config: ProxyConfig):
        self.proxy_config = proxy_config
        self.logger = logging.getLogger(__name__)
        self._cookies = None

    @abstractmethod
    def _get_cookies(self) -> Dict:
        pass

    @abstractmethod
    def _run(self, item_id: str) -> VintedItemStatus:
        pass

    @abstractmethod
    def run(self, item_ids: List[str]) -> List[Dict]:
        pass


class AsyncAvailabilityChecker(BaseAvailabilityChecker):
    async def run(self, item_ids: List[str]) -> List[VintedItemStatus]:
        if not item_ids:
            return []

        if not self._cookies:
            self._cookies = await self._get_cookies()

        coroutines = [self._run(item_id) for item_id in item_ids]
        results = await asyncio.gather(*coroutines)

        return results

    async def _get_cookies(self) -> Dict:
        headers = {**self.BASE_HEADERS, "Referer": self.BASE_URL}

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    self.BASE_URL,
                    headers=headers,
                    proxy=self.proxy_config.url,
                    allow_redirects=True,
                    timeout=30,
                ) as response:
                    if not response.ok:
                        raise Exception(f"Failed to get cookies: {response.status}")

                    return {
                        cookie.key: cookie.value for cookie in response.cookies.values()
                    }

        except Exception as e:
            self.logger.error(f"Error getting cookies: {e}")
            raise

    async def _run(self, item_id: str) -> VintedItemStatus:
        headers = {**self.BASE_HEADERS, "Referer": self.BASE_URL}
        url = self.BASE_API_URL.format(item_id)

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    url,
                    headers=headers,
                    cookies=self._cookies,
                    proxy=self.proxy_config.url,
                    allow_redirects=True,
                    timeout=30,
                ) as response:
                    status_code = response.status

                    if not response.ok:
                        return VintedItemStatus(
                            item_id=item_id,
                            is_available=False,
                            status_code=status_code,
                            error=f"HTTP {status_code}",
                        )

                    try:
                        data = await response.json()
                        item_info = data.get("item", {})
                        is_available = bool(
                            item_info and not item_info.get("is_closed", False)
                        )

                        return VintedItemStatus(
                            item_id=item_id,
                            is_available=is_available,
                            status_code=status_code,
                        )

                    except Exception as e:
                        return VintedItemStatus(
                            item_id=item_id,
                            is_available=False,
                            status_code=status_code,
                            error=f"Failed to parse response: {str(e)}",
                        )

        except asyncio.TimeoutError:
            return VintedItemStatus(
                item_id=item_id,
                is_available=False,
                status_code=408,
                error="Request timeout",
            )


class AvailabilityChecker(BaseAvailabilityChecker):
    def run(self, item_ids: List[str]) -> List[VintedItemStatus]:
        if not item_ids:
            return []

        if not self._cookies:
            self._cookies = self._get_cookies()

        n, n_success = 0, 0
        results = []
        loop = tqdm(iterable=item_ids, total=len(item_ids))

        for item_id in loop:
            response = self._run(item_id)
            results.append(response)

            n += 1
            n_success += int(response.ok)
            loop.set_description(f"Success: {n_success/n:.2f}")

        return results

    def _get_cookies(self) -> Dict:
        headers = {**self.BASE_HEADERS, "Referer": self.BASE_URL}

        try:
            response = requests.get(
                self.BASE_URL,
                headers=headers,
                proxies={"http": self.proxy_config.url, "https": self.proxy_config.url},
                allow_redirects=True,
                timeout=30,
            )

            if not response.ok:
                raise Exception(f"Failed to get cookies: {response.status_code}")

            return {cookie.name: cookie.value for cookie in response.cookies}

        except Exception as e:
            self.logger.error(f"Error getting cookies: {e}")
            raise

    def _run(self, item_id: str) -> VintedItemStatus:
        headers = {**self.BASE_HEADERS, "Referer": self.BASE_URL}
        url = self.BASE_API_URL.format(item_id)

        try:
            response = requests.get(
                url,
                headers=headers,
                cookies=self._cookies,
                proxies={"http": self.proxy_config.url, "https": self.proxy_config.url},
                allow_redirects=True,
                timeout=30,
            )
            status_code = response.status_code

            if not response.ok:
                return VintedItemStatus(
                    item_id=item_id,
                    is_available=False,
                    status_code=status_code,
                    error=f"HTTP {status_code}",
                )

            try:
                data = response.json()
                item_info = data.get("item", {})
                is_available = bool(item_info and not item_info.get("is_closed", False))

                return VintedItemStatus(
                    item_id=item_id,
                    is_available=is_available,
                    status_code=status_code,
                )

            except Exception as e:
                return VintedItemStatus(
                    item_id=item_id,
                    is_available=False,
                    status_code=status_code,
                    error=f"Failed to parse response: {str(e)}",
                )

        except requests.Timeout:
            return VintedItemStatus(
                item_id=item_id,
                is_available=False,
                status_code=408,
                error="Request timeout",
            )
