from typing import List, Optional
from dataclasses import dataclass


@dataclass
class ProxyConfig:
    password: str
    proxy_group: str = "RESIDENTIAL"
    country_code: str = "FR"
    _hostname: str = "proxy.apify.com"
    _port: int = 8000

    @property
    def url(self) -> str:
        return f"http://groups-{self.proxy_group},country-{self.country_code}:{self.password}@{self._hostname}:{self._port}"
