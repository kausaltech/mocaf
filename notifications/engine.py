from typing import Any, Dict, List, Optional
from django.conf import settings

from mocaf.geniem_api import GeniemApi
from trips.models import Device


class NotificationEngine(GeniemApi):
    identifier = 'geniem'

    def __init__(self, api_url=None, api_token=None):
        if api_url is None:
            api_url = settings.GENIEM_NOTIFICATION_API_BASE
        if api_token is None:
            api_token = settings.GENIEM_NOTIFICATION_API_TOKEN
        super().__init__(api_url, api_token)

    def send_notification(self, devices: List[Device], title: Dict[str, str], content: Dict[str, str], extra_data: Optional[Dict[str, Any]] = None):
        title_data = {'title%s' % lang.capitalize(): val for lang, val in title.items()}
        content_data = {'content%s' % lang.capitalize(): val for lang, val in content.items()}
        if not extra_data:
            extra_data = {}
        data = dict(
            uuids=[str(dev.uuid) for dev in devices],
            **title_data,
            **content_data,
            **extra_data,
        )
        return self.post(data)
