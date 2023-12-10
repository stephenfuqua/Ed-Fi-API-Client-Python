import json
from datetime import datetime, timedelta

from swagger_client.rest import ApiException
from swagger_client.configuration import Configuration
from swagger_client.api_client import ApiClient

class TokenManager(object):

    """
    Creates a new instance of the TokenManager.

    Parameters
    ---------
    token_url: str
        The token URL for the Ed-Fi API.
    configuration: Configuration
        A list dictionary of configuration options for the RESTClientObject.
        Must study the RESTClientObject constructor carefully to understand the
        available options.
    """
    def __init__(self, token_url: str, configuration: Configuration) -> None:
        assert token_url is not None
        assert token_url.strip() != ""

        self.token_url: str = token_url
        self.configuration: Configuration = configuration
        self.client: ApiClient = ApiClient(self.configuration)
        self.expires_at = datetime.now()

    def _authenticate(self) -> None:
        post_params = {
            "grant_type": "client_credentials",
            "client_id": self.configuration.username,
            "client_secret": self.configuration.password
        }
        headers = {
            "Content-Type": "application/x-www-form-urlencoded"
        }

        token_response = self.client.request("POST", self.token_url, headers=headers, post_params=post_params)

        data = json.loads(token_response.data)
        self.expires_at = datetime.now() + timedelta(seconds=data["expires_in"])
        self.configuration.access_token = data["access_token"]

    """
    Sends a token request and creates an ApiClient containing the returned access token.

    Returns
    ------
    ApiClient
        an ApiClient instance that has already been authenticated.
    """
    def create_authenticated_client(self) -> ApiClient:

        self._authenticate()

        return self.client

    """
    Re-authenticates if the token has expired.
    """
    def refresh(self) -> None:
        if datetime.now() > self.expires_at:
            self._authenticate()
        else:
            raise ApiException("Token is not expired; authentication failure may be a configuration problem.")
