import generation_uptimes_dao


def test_generate_uptime_list():
    uptime_duration = 60
    size = 100000
    result = generation_uptimes_dao._generate_uptime_list(uptime_duration, size)

    assert len(result) == size
    hour = 0
    min_uptime, max_uptime = 0, 3600
    offset = max_uptime + uptime_duration + 5
    for uptime, uptime_duration in result:
        assert uptime_duration == 60
        assert min_uptime + hour*offset <= uptime <= max_uptime + hour*offset
        hour += 1
