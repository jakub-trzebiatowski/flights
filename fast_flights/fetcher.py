from typing import TypeVar, overload

from primp import Client
from selectolax.lexbor import LexborHTMLParser

from .exceptions import ResultsNotParseable
from .integrations.base import DataSourceIntegration, FetchIntegration
from .parser import ResultList, parse
from .querying import Query

URL = "https://www.google.com/travel/flights"
CONSENT_HOST = "consent.google.com"


T = TypeVar("T")


@overload
def get_flights(
    q: Query | str, /, *, proxy: str | None = None, integration: None = None
) -> ResultList: ...


@overload
def get_flights(
    q: Query | str, /, *, proxy: str | None = None, integration: FetchIntegration
) -> ResultList: ...


@overload
def get_flights(
    q: Query | str,
    /,
    *,
    proxy: str | None = None,
    integration: DataSourceIntegration[T],
) -> T: ...


def get_flights(
    q: Query | str,
    /,
    *,
    proxy: str | None = None,
    integration: FetchIntegration | DataSourceIntegration[T] | None = None,
) -> T | ResultList:
    """Get flights.

    Args:
        q: The query.
        proxy (optional): Proxy, if you're using `fast-flight`'s default fetcher.
        integration (optional): Plug-in integration.
    """
    if integration is not None and isinstance(integration, DataSourceIntegration):
        return integration.fetch(q)

    html = fetch_flights_html(q, proxy=proxy, fetch_integration=integration)
    return parse(html)


def fetch_flights_html(
    q: Query | str,
    /,
    *,
    proxy: str | None = None,
    fetch_integration: FetchIntegration | None = None,
) -> str:
    """Fetch flights and get the **HTML**.

    Args:
        q: The query.
        proxy (str, optional): Proxy.
    """
    if fetch_integration is None:
        client = Client(
            impersonate="chrome_145",
            impersonate_os="macos",
            referer=True,
            proxy=proxy,
            cookie_store=True,
        )

        if isinstance(q, Query):
            params = q.params()

        else:
            params = {"q": q}

        res = client.get(URL, params=params)

        if CONSENT_HOST in res.url:
            res = _dismiss_consent(client, res.text)

        return res.text

    else:
        return fetch_integration.fetch_html(q)


def _dismiss_consent(client: Client, html: str):
    """Answer Google's cookie consent interstitial and follow it through.

    Served in regions where consent is mandatory (the EEA and the UK). The page
    offers a "reject all" and an "accept all" form; we submit the former, which
    keeps only the strictly necessary cookies and still lets the request
    continue to the results page.
    """
    parser = LexborHTMLParser(html)

    for form in parser.css("form"):
        fields = {
            name: node.attributes.get("value") or ""
            for node in form.css("input[name]")
            if (name := node.attributes.get("name"))
        }

        # The reject-all form is the one opting out of the extra consent
        # modes; the accept-all variant sets them to true instead.
        if fields.get("set_eom") != "true":
            continue

        action = form.attributes.get("action")
        if action:
            return client.post(action, data=fields)

    raise ResultsNotParseable(
        "received a consent page but could not find the consent form; "
        "pass a proxy outside the EEA/UK to bypass it"
    )
