from typing import Dict, List, Optional

from abc import ABC, abstractmethod
from dataclasses import dataclass
import random


class BaseProxyConfig(ABC):
    @property
    @abstractmethod
    def url(self) -> str:
        pass


@dataclass
class WebshareProxy:
    host: str
    port: int
    username: str
    password: str

    @classmethod
    def from_dict(cls, data: Dict[str, str]) -> "WebshareProxy":
        return cls(
            host=data["host"],
            port=int(data["port"]),
            username=data["username"],
            password=data["password"],
        )


@dataclass
class SimpleProxy:
    host: str
    port: int = 80


@dataclass
class WebshareProxyConfig(BaseProxyConfig):
    proxies: List[WebshareProxy]
    _last_proxy_host: Optional[str] = None

    @property
    def url(self) -> str:
        available_proxies = self.get_available_proxies()
        proxy = random.choice(available_proxies)
        self._last_proxy_host = proxy.host

        return f"http://{proxy.username}:{proxy.password}@{proxy.host}:{proxy.port}/"

    @classmethod
    def from_dict(cls, data: Dict[str, str]) -> "WebshareProxyConfig":
        proxies = [WebshareProxy.from_dict(data)]
        return cls(proxies=proxies)

    @classmethod
    def from_list(
        cls, proxies: List[Dict[str, str]]
    ) -> Optional["WebshareProxyConfig"]:
        if not proxies:
            return None

        proxies = [WebshareProxy.from_dict(p) for p in proxies]

        return cls(proxies=proxies)

    def get_available_proxies(self) -> List[WebshareProxy]:
        available_proxies = [p for p in self.proxies if p.host != self._last_proxy_host]

        if not available_proxies:
            available_proxies = self.proxies

        return available_proxies


@dataclass
class ApifyProxyConfig(BaseProxyConfig):
    password: str
    country_code: str = "FR"
    _hostname: str = "proxy.apify.com"
    _port: int = 8000

    @property
    def url_datacenter(self) -> str:
        username = f"auto:{self.password}"
        return f"http://{username}@{self._hostname}:{self._port}"

    @property
    def url_residential(self) -> str:
        username = f"groups-RESIDENTIAL,country-{self.country_code}:{self.password}"
        return f"http://{username}@{self._hostname}:{self._port}"

    @property
    def url(self) -> str:
        return self.url_residential


@dataclass
class SimpleProxyConfig(BaseProxyConfig):
    proxies: List[SimpleProxy]
    _last_proxy_host: Optional[str] = None

    @property
    def url(self) -> str:
        available_proxies = self.get_available_proxies()
        proxy = random.choice(available_proxies)
        self._last_proxy_host = proxy.host

        return f"http://{proxy.host}:{proxy.port}"

    @classmethod
    def from_list(cls, ips: List[str], port: int = 80) -> "SimpleProxyConfig":
        proxies = [SimpleProxy(host=ip, port=port) for ip in ips]
        return cls(proxies=proxies)

    def get_available_proxies(self) -> List[SimpleProxy]:
        available_proxies = [p for p in self.proxies if p.host != self._last_proxy_host]

        if not available_proxies:
            available_proxies = self.proxies

        return available_proxies


@dataclass
class ProxyConfig(BaseProxyConfig):
    _proxy: BaseProxyConfig

    @property
    def url(self) -> str:
        return self._proxy.url

    @classmethod
    def from_webshare(cls, proxy: WebshareProxyConfig) -> "ProxyConfig":
        return cls(_proxy=proxy)

    @classmethod
    def from_apify(cls, proxy: ApifyProxyConfig) -> "ProxyConfig":
        return cls(_proxy=proxy)

    @classmethod
    def from_ip_list(cls, ips: List[str], port: int = 80) -> "ProxyConfig":
        return cls(_proxy=SimpleProxyConfig.from_list(ips, port=port))
