from typing import Dict, List, Optional
from abc import ABC, abstractmethod

import logging, asyncio, aiohttp
import requests
from tqdm import tqdm

from src.models import ProxyConfig, VintedItemStatus
from src.enums import MAX_RETRIES, INITIAL_SLEEP_TIME, MAX_SLEEP_TIME


class BaseAvailabilityChecker(ABC):
    BASE_HEADERS = {
        "Accept": "application/json",
        "Accept-Language": "en-US,en;q=0.9",
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    }

    BASE_URL = "https://www.vinted.fr"
    BASE_API_URL = "https://www.vinted.fr/api/v2/items/{}/details"

    def __init__(self, proxy_config: Optional[ProxyConfig] = None):
        self.proxy_config = proxy_config
        self.logger = logging.getLogger(__name__)
        self._cookies = None

    @abstractmethod
    def get_cookies(self) -> Dict:
        pass

    @abstractmethod
    def _run(self, item_id: str) -> VintedItemStatus:
        pass

    @abstractmethod
    def run(self, item_ids: List[str], use_proxy: bool = False) -> List[Dict]:
        pass

    def check_is_available(self, json_data: Dict) -> bool:
        item_info = json_data.get("item", {})
        is_available = bool(item_info and not item_info.get("is_closed", False))

        return is_available


class AsyncAvailabilityChecker(BaseAvailabilityChecker):
    async def run(
        self, item_ids: List[str], use_proxy: bool = False
    ) -> List[VintedItemStatus]:
        if not item_ids:
            return []

        self._cookies = await self.get_cookies()
        coroutines = [self._run(item_id, use_proxy) for item_id in item_ids]
        results = await asyncio.gather(*coroutines)

        return results

    async def get_cookies(
        self, retry_count: int = 0, sleep_time: int = INITIAL_SLEEP_TIME
    ) -> Dict:
        if retry_count >= MAX_RETRIES:
            raise Exception(f"Failed to get cookies after {MAX_RETRIES} retries")

        headers = {**self.BASE_HEADERS, "Referer": self.BASE_URL}

        kwargs = {
            "headers": headers,
            "allow_redirects": True,
            "timeout": 30,
            "proxy": self.proxy_config.url if self.proxy_config else None,
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(self.BASE_URL, **kwargs) as response:
                    if not response.ok:
                        await asyncio.sleep(min(sleep_time, MAX_SLEEP_TIME))

                        return await self.get_cookies(retry_count + 1, sleep_time * 2)

                    return {
                        cookie.key: cookie.value for cookie in response.cookies.values()
                    }

        except Exception as e:
            self.logger.error(
                f"Error getting cookies (attempt {retry_count + 1}/{MAX_RETRIES}): {e}"
            )
            await asyncio.sleep(min(sleep_time, MAX_SLEEP_TIME))
            return await self.get_cookies(retry_count + 1, sleep_time * 2)

    async def _run(self, item_id: str, use_proxy: bool = False) -> VintedItemStatus:
        headers = {**self.BASE_HEADERS, "Referer": self.BASE_URL}
        url = self.BASE_API_URL.format(item_id)

        kwargs = {
            "headers": headers,
            "cookies": self._cookies,
            "allow_redirects": True,
            "timeout": 30,
        }

        if use_proxy and self.proxy_config:
            kwargs["proxy"] = self.proxy_config.url

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, **kwargs) as response:
                    status_code = response.status

                    try:
                        data = await response.json()

                        return VintedItemStatus(
                            item_id=item_id,
                            is_available=self.check_is_available(data),
                            status_code=status_code,
                        )

                    except Exception as e:
                        return VintedItemStatus(
                            item_id=item_id,
                            is_available=False,
                            status_code=status_code,
                            error=f"Failed to parse response: {str(e)}",
                        )

        except Exception as e:
            return VintedItemStatus(
                item_id=item_id,
                is_available=False,
                status_code=505,
                error=str(e),
            )


class AvailabilityChecker(BaseAvailabilityChecker):
    def run(self, item_ids: List[str]) -> List[VintedItemStatus]:
        if not item_ids:
            return []

        if not self._cookies:
            self._cookies = self.get_cookies()

        n, n_success = 0, 0
        results = []
        loop = tqdm(iterable=item_ids, total=len(item_ids))

        for item_id in loop:
            response = self._run(item_id)
            results.append(response)

            n += 1
            n_success += int(response.ok)
            loop.set_description(f"Success: {n_success / n:.2f}")

        return results

    def get_cookies(self) -> Dict:
        headers = {**self.BASE_HEADERS, "Referer": self.BASE_URL}

        kwargs = {
            "headers": headers,
            "allow_redirects": True,
            "timeout": 30,
        }

        if self.proxy_config:
            kwargs["proxies"] = {
                "http": self.proxy_config.url,
                "https": self.proxy_config.url,
            }

        try:
            response = requests.get(self.BASE_URL, **kwargs)

            if not response.ok:
                raise Exception(f"Failed to get cookies: {response.status_code}")

            return {cookie.name: cookie.value for cookie in response.cookies}

        except Exception as e:
            self.logger.error(f"Error getting cookies: {e}")
            raise

    def _run(self, item_id: str) -> VintedItemStatus:
        headers = {**self.BASE_HEADERS, "Referer": self.BASE_URL}
        url = self.BASE_API_URL.format(item_id)

        kwargs = {
            "headers": headers,
            "cookies": self._cookies,
            "allow_redirects": True,
            "timeout": 30,
        }

        if self.proxy_config:
            kwargs["proxies"] = {
                "http": self.proxy_config.url,
                "https": self.proxy_config.url,
            }

        try:
            response = requests.get(url, **kwargs)

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

                return VintedItemStatus(
                    item_id=item_id,
                    is_available=self.check_is_available(data),
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
