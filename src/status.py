import requests

from .vinted import Vinted, VintedResponse
from .models import ItemStatus
from .enums import *
from .utils import retry_with_backoff, parse_web_content


def is_available(item_status: ItemStatus) -> bool:
    if item_status in [ItemStatus.AVAILABLE, ItemStatus.UNKNOWN]:
        return True
    else:
        return False


def get_status_api(client: Vinted, item_id: int) -> ItemStatus:
    def func():
        return client.item_info(item_id)

    response = retry_with_backoff(func)

    if response is None:
        return ItemStatus.UNKNOWN

    return _parse_status_api(response)


def get_status_requests(item_url: str) -> ItemStatus:
    def func():
        return requests.get(item_url, headers=REQUESTS_HEADERS)

    response = retry_with_backoff(func)

    if response is None:
        return ItemStatus.UNKNOWN

    if response.status_code == 404:
        return ItemStatus.NOT_FOUND

    if response.url != item_url:
        return ItemStatus.NOT_FOUND

    return parse_web_content(response.content)


def _parse_status_api(response: VintedResponse) -> ItemStatus:
    if response.status_code == 404:
        return ItemStatus.NOT_FOUND

    elif response.status_code == 200 and response.data:
        item_info = response.data.get("item")
        if not item_info:
            return ItemStatus.SOLD

        is_available = item_info.get("can_be_sold")
        if is_available == False:
            return ItemStatus.SOLD
        elif is_available == True:
            return ItemStatus.AVAILABLE

        is_closed = item_info.get("is_closed")
        if is_closed == True:
            return ItemStatus.SOLD
        elif is_closed == False:
            return ItemStatus.AVAILABLE

        return ItemStatus.UNKNOWN

    else:
        return ItemStatus.UNKNOWN
