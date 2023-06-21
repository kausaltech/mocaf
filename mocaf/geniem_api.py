import requests


class GeniemApi:
    def __init__(self, api_url, api_token):
        self.api_url = api_url
        self.api_token = api_token

    def is_enabled(self) -> bool:
        return bool(self.api_url and self.api_token)

    def post(self, data):
        assert self.is_enabled()
        response = requests.post(
            self.api_url, json=data, headers=dict(apikey=self.api_token),
            timeout=30,
        )
        response.raise_for_status()
        return response
