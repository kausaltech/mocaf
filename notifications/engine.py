from typing import Dict, List
import requests
from django.conf import settings

from trips.models import Device


class NotificationEngine:
    def __init__(self):
        self.api_url = settings.GENIEM_NOTIFICATION_API_BASE
        self.api_token = settings.GENIEM_NOTIFICATION_API_TOKEN

    def is_enabled(self):
        return self.api_url and self.api_token

    def send_notification(self, devices: List[Device], title: Dict[str, str], content: Dict[str, str]):
        assert self.is_enabled()

        title_data = {'title%s' % lang.capitalize(): val for lang, val in title.items()}
        content_data = {'content%s' % lang.capitalize(): val for lang, val in content.items()}
        data = dict(
            uuids=[str(dev.uuid) for dev in devices],
            **title_data,
            **content_data,
        )
        resp = requests.post(
            self.api_url, json=data, headers=dict(apikey=self.api_token),
            timeout=30,
        )
        resp.raise_for_status()