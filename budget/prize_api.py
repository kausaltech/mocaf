from django.conf import settings

from mocaf.geniem_api import GeniemApi


class PrizeApi(GeniemApi):
    def __init__(self, api_url=None, api_token=None):
        if api_url is None:
            api_url = settings.GENIEM_PRIZE_API_BASE
        if api_token is None:
            api_token = settings.GENIEM_PRIZE_API_TOKEN
        super().__init__(api_url, api_token)

    def award(self, prizes):
        # FIXME: This awards prizes to all devices of an account, but prizes should be specific to an account.
        # Seems to be not yet supported by API.
        data = [{
            'uuid': str(device.uuid),
            'level': prize.budget_level.identifier,
            'year': prize.prize_month_start.year,
            'month': prize.prize_month_start.month,
        } for prize in prizes for device in prize.account.devices.all()]
        return self.post(data)
