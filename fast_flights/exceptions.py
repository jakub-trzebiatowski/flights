class FlightsNotFound(Exception):
    """No flights were found."""


class ResultsNotParseable(Exception):
    """The response did not contain a flight results payload.

    Usually means Google served something other than the results page, e.g. a
    cookie consent interstitial, a captcha, or a rate limit notice.
    """
