from datetime import datetime, timedelta, timezone

from checkins import same_day

UTC = timezone.utc
DENVER = timezone(timedelta(hours=-6))


def test_evening_in_denver_is_one_day():
    nine_pm = datetime(2026, 7, 4, 3, 0, tzinfo=UTC)    # 9pm on Jul 3 in Denver
    eleven_pm = datetime(2026, 7, 4, 5, 0, tzinfo=UTC)  # 11pm on Jul 3 in Denver
    early = datetime(2026, 7, 3, 23, 0, tzinfo=UTC)     # 5pm on Jul 3 in Denver
    assert same_day(nine_pm, eleven_pm, DENVER)
    assert same_day(early, nine_pm, DENVER)
