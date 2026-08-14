# Apple Ads Platform API Python

A Python client library for the Apple Ads Platform API.

## Model and Endpoint Documentation

This README serves as the primary documentation for installation and usage of this library. For
information on data models and API endpoints, see the
[Apple Ads Platform API documentation](https://developer.apple.com/documentation/apple-ads-platform-api)
found on Apple's developer website.

## Installation

Install this library from PyPI. Like nearly any software dependency, you should pin a specific
version and update it only when you explicitly intend to do so.

pip:

```bash
pip install apple-ads-platform==VERSION
```

Poetry (`pyproject.toml`):

```toml
[project]
dependencies = [
    "apple-ads-platform==VERSION",
]
```

This library requires Python 3.12 or newer.

## Getting Started

This library makes it easy to construct an
[`AppleAdsApi`](apple_ads_platform/api/apple_ads_api.py) instance that is ready to call the Apple
Ads Platform API. The
[`AppleAdsClientBuilder`](apple_ads_platform/builder.py) accepts the information required for
authentication as well as various optional settings. The resulting client performs the OAuth flow
transparently.

### Client Construction

You can instantiate a client in three ways.

#### Using Your Private Key

The first way to create the client is to provide your private key along with the rest of the
associated metadata. The library creates a client secret using your private key every time
a new access token is needed.

```python
from apple_ads_platform.builder import AppleAdsClientBuilder

client_id = "..."
team_id = "..."
key_id = "..."
private_key = get_private_key_from_secure_place()

api = AppleAdsClientBuilder.from_private_key(
    client_id, team_id, key_id, private_key
).build()
```

You can also provide a path to a file containing your private key. This route is otherwise the
same as above.

```python
from apple_ads_platform.builder import AppleAdsClientBuilder

client_id = "..."
team_id = "..."
key_id = "..."
private_key_path = "...path/to/your/private/key/file"

api = AppleAdsClientBuilder.from_private_key_path(
    client_id, team_id, key_id, private_key_path
).build()
```

#### Using a Custom ClientSecretProvider

If you wish to generate client secrets in a different way (for example generating
them offline and using a fixed one at runtime, or using a separate service for
signing), you can use the builder factory method which accepts an instance of
[`ClientSecretProvider`](apple_ads_platform/auth/protocols.py). The library
calls this object whenever a client secret is needed for fetching a new access token.

```python
from apple_ads_platform.auth.fixed_client_secret import FixedClientSecretProvider
from apple_ads_platform.builder import AppleAdsClientBuilder

client_id = "..."
client_secret = "..."

client_secret_provider = FixedClientSecretProvider(client_secret)

api = AppleAdsClientBuilder.from_client_secret_provider(
    client_id, client_secret_provider
).build()
```

Any object that implements the `ClientSecretProvider` protocol (a single `create_secret() -> str`
method) is accepted — no explicit subclass is required.

#### Implementing OAuth Yourself

We recommend letting the library handle the OAuth flow. If you have specific requirements, you can
implement it yourself by constructing the client with an
[`AccessTokenProvider`](apple_ads_platform/auth/protocols.py).
In this case, the library calls this object before every API request in order to attach an access
token as an HTTP header.

```python
from apple_ads_platform.builder import AppleAdsClientBuilder

# my_token_provider must implement AccessTokenProvider (a single get_token() -> str method)
my_token_provider = MyAccessTokenProvider(...)

api = AppleAdsClientBuilder.from_access_token_provider(my_token_provider).build()
```

### Optional Settings

The builder provides the following chainable configuration methods. All have sensible defaults
and can be omitted.

| Method              | Argument Type       | Description                                                                                                                                                                                     | Default                       |
|---------------------|---------------------|-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|-------------------------------|
| `api_timeout`       | `float`             | Request timeout (in seconds) for the main API client.                                                                                                                                           | `5.0`                         |
| `api_log_level`     | `Optional[LogLevel]`| Logging level for the main API client. Pass `None` to disable logging entirely for these calls.                                                                                                 | `None` (no logging)           |
| `api_proxy`         | `str`               | Proxy URL for the main API client.                                                                                                                                                              | None                          |
| `api_proxy_headers` | `dict`              | Proxy headers for the main API client. Requires `api_proxy` to also be set.                                                                                                                     | None                          |
| `auth_timeout`      | `float`             | Request timeout (in seconds) for the auth client. Not applicable when the builder was created via `from_access_token_provider`.                                                                 | `5.0`                         |
| `auth_log_level`    | `Optional[LogLevel]`| Logging level for the auth client. Pass `None` to disable logging. `LogLevel.BODY` is rejected because auth bodies contain credentials. Not applicable when using `from_access_token_provider`. | `None` (no logging)           |
| `auth_proxy`        | `str`               | Proxy URL for the auth client. Not applicable when the builder was created via `from_access_token_provider`.                                                                                    | None                          |
| `auth_proxy_headers`| `dict`              | Proxy headers for the auth client. Requires `auth_proxy` to also be set. Not applicable when the builder was created via `from_access_token_provider`.                                          | None                          |

`LogLevel` is defined in [`apple_ads_platform.log_level`](apple_ads_platform/log_level.py) and
has the values `BASIC`, `HEADERS`, and `BODY`.

#### Example with Optional Settings

```python
from apple_ads_platform.builder import AppleAdsClientBuilder
from apple_ads_platform.log_level import LogLevel

api = (
    AppleAdsClientBuilder
    .from_private_key(client_id, team_id, key_id, private_key)
    .api_log_level(LogLevel.BODY)
    .build()
)
```

## Examples

Every request requires the `X-AP-Context` header, which is passed as the `x_ap_context` argument
to each API method. It is a string of the form`adAccountId=<adAccountId>;`. See the API
documentation for details.

#### Query Running Campaigns
```python
from apple_ads_platform.builder import AppleAdsClientBuilder
from apple_ads_platform.models.campaign_system_status import CampaignSystemStatus
from apple_ads_platform.models.query_filter import QueryFilter
from apple_ads_platform.models.query_filter_operator import QueryFilterOperator
from apple_ads_platform.models.query_request import QueryRequest

api = AppleAdsClientBuilder.from_private_key(
    client_id, team_id, key_id, private_key
).build()

running_campaigns_request = QueryRequest(
    filters=[
        QueryFilter(
            field="systemStatus",
            operator=QueryFilterOperator.EQUALS,
            value=CampaignSystemStatus.RUNNING,
        ),
    ],
)

context_header = f"adAccountId={ad_account_id};"

response = api.campaigns_query_post(context_header, running_campaigns_request)
```

#### Get a Business Brand by ID
```python
from apple_ads_platform.builder import AppleAdsClientBuilder

api = AppleAdsClientBuilder.from_private_key(
    client_id, team_id, key_id, private_key
).build()

brand_id = "..."
context_header = f"adAccountId={ad_account_id};"

response = api.get_brand(context_header, brand_id)
```

#### Update a Keyword Bid
```python
from apple_ads_platform.builder import AppleAdsClientBuilder
from apple_ads_platform.models.keyword_update import KeywordUpdate
from apple_ads_platform.models.money import Money

api = AppleAdsClientBuilder.from_private_key(
    client_id, team_id, key_id, private_key
).build()

keyword_id = "..."
context_header = f"adAccountId={ad_account_id};"

keyword_update = KeywordUpdate(bid=Money(amount="1.00", currency="USD"))

response = api.keywords_id_put(keyword_id, context_header, keyword_update)
```

## Keeping Your Credentials Secure

Your private key and client secrets are sensitive credentials. Don't store them as plain text.
Treat access tokens as secrets too. The library does not log any of these values. Do the same if
you choose to add any additional logging or observability.

## Thread Safety

When constructed with a private key or `ClientSecretProvider`, the client is thread-safe. Create a
single instance and share it across your entire application. This maximizes the
benefit of connection pooling and minimizes calls to the OAuth server. If you provide your own
`AccessTokenProvider`, thread-safety depends on the implementation.

## Enum Classes

This library uses enum classes throughout the API model. As the API itself evolves over time, new
enum cases may appear. To prevent deserialization errors when this happens, every enum class contains
a special case `UNKNOWN_DEFAULT_OPEN_API`, which will be selected when deserializing API responses
that contain a string value that doesn't match an existing enum case. You can compare against this
case to detect when this has happened. Keep your library up to date to ensure you have model classes
that match the latest version of the API.

## License

This project is released under the MIT License. See [LICENSE](LICENSE) for details.

This project includes third-party software components; see [ACKNOWLEDGEMENTS](ACKNOWLEDGEMENTS) for attribution.