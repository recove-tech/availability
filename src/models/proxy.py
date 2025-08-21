from dataclasses import dataclass


@dataclass
class ProxyConfig:
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