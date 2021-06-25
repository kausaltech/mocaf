from typing import Dict, List
from django.conf import settings

from mocaf.geniem_api import GeniemApi
from trips.models import Device


class NotificationEngine(GeniemApi):
    def __init__(self, api_url=None, api_token=None):
        if api_url is None:
            api_url = settings.GENIEM_NOTIFICATION_API_BASE
        if api_token is None:
            api_token = settings.GENIEM_NOTIFICATION_API_TOKEN
        super().__init__(api_url, api_token)

    def send_notification(self, devices: List[Device], title: Dict[str, str], content: Dict[str, str]):
        title_data = {'title%s' % lang.capitalize(): val for lang, val in title.items()}
        content_data = {'content%s' % lang.capitalize(): val for lang, val in content.items()}
        data = dict(
            uuids=[str(dev.uuid) for dev in devices],
            **title_data,
            **content_data,
        )
        return self.post(data)
