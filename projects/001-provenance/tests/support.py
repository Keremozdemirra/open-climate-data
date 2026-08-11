import datetime as dt
import random

from provenance.record import Provenance

BASE = dt.datetime(2025, 1, 1, tzinfo=dt.timezone.utc)


def rec(n=0, **overrides):
    kwargs = dict(
        source="Source %d" % n,
        dataset="dataset-%d" % n,
        version="v%d" % n,
        retrieved_at=BASE + dt.timedelta(days=n),
        licence="CC-BY-4.0",
        query={"country": "AA", "year": 2024 + (n % 2)},
        url="https://example.invalid/%d" % n,
        note="",
    )
    kwargs.update(overrides)
    return Provenance(**kwargs)


def rng_for(seed):
    return random.Random(seed)
