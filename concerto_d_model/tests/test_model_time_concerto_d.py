import json

from concerto_d_model import model_time_concerto_d
from concerto_d_model.model_time_concerto_d import _compute_receive_periods_from_sending_periods, \
    count_active_intervals, count_active_intervals_sending, _compute_reconf_periods_per_node, \
    _compute_sending_periods_per_node, _get_deploy_parallel_use_case_model


def test_compute_uses_overlaps_with_provide():
    uptimes_periods_per_node_0 = {
        0: [[0, 10]],
        1: [[0, 10]]
    }
    uptimes_periods_per_node_1 = {
        0: [[1, 10], [12, 20]],
        1: [[5, 15]],
        2: [[15, 17], [25, 30]],
        3: [[0, 25]]
    }
    assert model_time_concerto_d._compute_uses_overlaps_with_provide(uptimes_periods_per_node_0) == {
        0: {1: [[0, 10]]},
        1: {0: [[0, 10]]}
    }
    assert model_time_concerto_d._compute_uses_overlaps_with_provide(uptimes_periods_per_node_1) == {
        0: {1: [[5, 10], [12, 15]], 2: [[15, 17]], 3: [[1, 10], [12, 20]]},
        1: {0: [[5, 10], [12, 15]], 2: [], 3: [[5, 15]]},
        2: {0: [[15, 17]], 1: [], 3: [[15, 17]]},
        3: {0: [[1, 10], [12, 20]], 1: [[5, 15]], 2: [[15, 17]]}
    }


def test_compute_uptimes_periods_per_node():
    uptime_schedule_0 = [
        [[0, 1], [90, 1]],
        [[5, 1], [60, 1]]
    ]
    uptime_schedule_1 = [
        [[0, 1], [100, 1]],
        [[10, 1], [80, 1]]
    ]
    uptime_schedule_2 = [
        [[0, 1], [-1, 1], [200, 1]],
        [[10.2, 1], [-1, 1]],
        [[0, 1], [-1, 1], [90, 1]],
    ]
    assert model_time_concerto_d._compute_uptimes_periods_per_node(uptime_schedule_0, 100) == {0: [[0, 50], [90, 100]], 1: [[5, 55], [60, 100]]}
    assert model_time_concerto_d._compute_uptimes_periods_per_node(uptime_schedule_1, 150) == {0: [[0, 50], [100, 150]], 1: [[10, 60], [80, 130]]}
    assert model_time_concerto_d._compute_uptimes_periods_per_node(uptime_schedule_2, 90.5) == {0: [[0, 50]], 1: [[10.2, 60.2]], 2: [[0, 50], [90, 90.5]]}


def test_compute_receive_periods_from_sending_periods():
    sending_periods_per_node_basic = {0: [[1, 0, 10]], 1: [[0, 10, 20]]}
    sending_periods_per_node_sort = {0: [[1, 2, 10], [1, 1, 5]], 1: [], 2: [[1, 5, 7]], 3: [[1, 1, 15]]}
    sending_periods_per_node_floating = {0: [[1, 0.5, 10.32]], 1: [[0, 10.0, 20.1]]}
    assert _compute_receive_periods_from_sending_periods(sending_periods_per_node_basic) == {0: [[1, 10, 20]], 1: [[0, 0, 10]]}
    assert _compute_receive_periods_from_sending_periods(sending_periods_per_node_sort) == {0: [], 1: [[0, 1, 5], [3, 1, 15], [0, 2, 10], [2, 5, 7]], 2: [], 3: []}
    assert _compute_receive_periods_from_sending_periods(sending_periods_per_node_floating) == {0: [[1, 10.0, 20.1]], 1: [[0, 0.5, 10.32]]}


def test_compute_merged_reconf_periods():
    basic = [[0, 5]]
    multiple = [[0, 5], [0, 5], [0, 5]]
    unsorted = [[4, 6], [0, 5], [2, 3]]
    floating = [[3.21, 5.55], [5.50, 5.54], [5.55, 5.56], [1.3, 3.19], [2.4, 6.7]]
    gaps = [[0, 5], [10, 20]]
    assert count_active_intervals(basic) == [[0, 5, 1]]
    assert count_active_intervals(multiple) == [[0, 5, 3]]
    assert count_active_intervals(unsorted) == [[0, 2, 1], [2, 3, 2], [3, 4, 1], [4, 5, 2], [5, 6, 1]]
    assert count_active_intervals(floating) == [[1.3, 2.4, 1], [2.4, 3.19, 2], [3.19, 3.21, 1], [3.21, 5.50, 2], [5.50, 5.54, 3], [5.54, 5.55, 2], [5.55, 5.56, 2], [5.56, 6.7, 1]]
    assert count_active_intervals(gaps) == [[0, 5, 1], [5, 10, 0], [10, 20, 1]]


def test_count_active_intervals_sending():
    basic = [[10, 0, 5]]
    multiple = [[10, 0, 5], [10, 0, 5], [11, 0, 5]]
    unsorted = [[9, 4, 6], [12, 0, 5], [8, 2, 3]]
    floating = [[10, 3.21, 5.55], [9, 5.50, 5.54], [10, 5.55, 5.56], [8, 1.3, 3.19], [9, 2.4, 6.7]]
    gaps = [[100, 0, 5], [100, 10, 20]]
    assert count_active_intervals_sending(basic) == [[0, 5, {10: 1}]]
    assert count_active_intervals_sending(multiple) == [[0, 5, {10: 2, 11: 1}]]
    assert count_active_intervals_sending(unsorted) == [[0, 2, {12: 1}], [2, 3, {12: 1, 8: 1}], [3, 4, {12: 1}], [4, 5, {9: 1, 12: 1}], [5, 6, {9: 1}]]
    assert count_active_intervals_sending(floating) == [[1.3, 2.4, {8: 1}], [2.4, 3.19, {9: 1, 8: 1}], [3.19, 3.21, {9: 1}], [3.21, 5.50, {10: 1, 9: 1}], [5.50, 5.54, {10: 1, 9: 2}], [5.54, 5.55, {9: 1, 10: 1}], [5.55, 5.56, {10: 1, 9: 1}], [5.56, 6.7, {9: 1}]]
    assert count_active_intervals_sending(gaps) == [[0, 5, {100: 1}], [5, 10, {}], [10, 20, {100: 1}]]


def test_compute_reconf_periods_per_node():
    esds_data_0 = {0: [{"reconf_period": [[0, 10], [20, 30]]}]}
    esds_data_1 = {0: [{"reconf_period": [[20, 30], [0, 10]]}]}
    esds_data_2 = {
        0: [{"reconf_period": [[20.5, 30.31], [0, 10]]}, {"reconf_period": [[100.3, 120.4], [500, 510], [320.1, 350.54]]}],
        1: [{"reconf_period": [[230, 280]]}]
    }

    expected_result_0 = {0: [[0, 10], [20, 30]]}
    expected_result_1 = {0: [[0, 10], [20, 30]]}
    expected_result_2 = {0: [[0, 10], [20.5, 30.31], [100.3, 120.4], [320.1, 350.54], [500, 510]], 1: [[230, 280]]}

    result_0 = _compute_reconf_periods_per_node(esds_data_0)
    result_1 = _compute_reconf_periods_per_node(esds_data_1)
    result_2 = _compute_reconf_periods_per_node(esds_data_2)

    assert result_0 == expected_result_0
    assert result_1 == expected_result_1
    assert result_2 == expected_result_2


def test_compute_sending_periods_per_node():
    esds_data_0 = {0: [{"connected_node_id": 1, "dct": 500, "reconf_period": [[10, 10]]}]}
    esds_data_1 = {3: [{"connected_node_id": 2, "dct": 100, "reconf_period": [[0, 10], [10, 20]]}]}
    esds_data_2 = {5: [{"connected_node_id": 3, "dct": 80, "reconf_period": [[50, 60], [70, 80], [30, 80], [10, 20]]}]}
    esds_data_3 = {
        10: [
            {"connected_node_id": 0, "dct": 50, "reconf_period": [[10, 50]]},
            {"connected_node_id": 1, "dct": 10, "reconf_period": [[0, 5], [6, 8]]},
        ],
        5: [
            {"connected_node_id": 10, "dct": 5.5, "reconf_period": [[2.3, 3.8]]}
        ]
    }

    expected_result_0 = {0: [[1, 10, 500]]}
    expected_result_1 = {3: [[2, 20, 100]]}
    expected_result_2 = {5: [[3, 80, 80]]}
    expected_result_3 = {10: [[1, 8, 10], [0, 50, 50]], 5: [[10, 3.8, 5.5]]}

    result_0 = _compute_sending_periods_per_node(esds_data_0)
    result_1 = _compute_sending_periods_per_node(esds_data_1)
    result_2 = _compute_sending_periods_per_node(esds_data_2)
    result_3 = _compute_sending_periods_per_node(esds_data_3)

    assert result_0 == expected_result_0
    assert result_1 == expected_result_1
    assert result_2 == expected_result_2
    assert result_3 == expected_result_3


class TestSyntheticUseCase:
    no_sleeping_nodes_schedules = [
        [[0, 1]],
        [[0, 1]],
        [[0, 1]],
        [[0, 1]],
        [[0, 1]],
        [[0, 1]],
    ]
    ud0_od0_15_25 = json.load(open("/home/aomond/concerto-d-projects/experiment_files/parameters/uptimes/mascots_uptimes-60-50-5-ud0_od0_15_25_perc.json"))
    ud1_od0_15_25 = json.load(open("/home/aomond/concerto-d-projects/experiment_files/parameters/uptimes/mascots_uptimes-60-50-5-ud1_od0_15_25_perc.json"))
    ud2_od0_15_25 = json.load(open("/home/aomond/concerto-d-projects/experiment_files/parameters/uptimes/mascots_uptimes-60-50-5-ud2_od0_15_25_perc.json"))
    ud0_od1_15_25 = json.load(open("/home/aomond/concerto-d-projects/experiment_files/parameters/uptimes/mascots_uptimes-60-50-5-ud0_od1_15_25_perc.json"))
    ud0_od2_15_25 = json.load(open("/home/aomond/concerto-d-projects/experiment_files/parameters/uptimes/mascots_uptimes-60-50-5-ud0_od2_15_25_perc.json"))
    ud0_od0_7_25 = json.load(open("/home/aomond/concerto-d-projects/experiment_files/parameters/uptimes/mascots_uptimes-60-50-5-ud0_od0_7_25_perc.json"))
    ud0_od0_30_25 = json.load(open("/home/aomond/concerto-d-projects/experiment_files/parameters/uptimes/mascots_uptimes-60-50-5-ud0_od0_30_25_perc.json"))

    def test_synthetic_use_case_100_overlaps(self):
        with open("/home/aomond/concerto-d-projects/experiment_files/parameters/transitions_times/transitions_times-1-30-deps12-0.json") as f:
            tts = json.load(f)["transitions_times"]

        t_scs = tts["server"]["t_sc"]
        list_deps, _ = _get_deploy_parallel_use_case_model(tts)
        for dep in list_deps:
            dep.nodes_schedules = self.no_sleeping_nodes_schedules

        (
            config0, config1, config2, config3, config4, service0, service1, service2, service3,
            service4, in_intermediate, in_config0, in_config1, in_config2, in_config3,
            in_config4, in_intermediate0, in_intermediate1, in_service0, in_service1, in_service2,
            in_service3, in_service4
        ) = list_deps

        version_concerto_d = "sync"
        assert config0.compute_time(version_concerto_d) == (1.26, [{0: {"start": 0, "end": 1.26}}])
        assert service0.compute_time(version_concerto_d) == (3.91, [{0: {"start": 1.26, "end": 3.91}}])
        assert config1.compute_time(version_concerto_d) == (14.07, [{0: {"start": 0, "end": 14.07}}])
        assert service1.compute_time(version_concerto_d) == (19.39, [{0: {"start": 14.07, "end": 19.39}}])
        assert config2.compute_time(version_concerto_d) == (1.69, [{0: {"start": 0, "end": 1.69}}])
        assert service2.compute_time(version_concerto_d) == (4.86, [{0: {"start": 1.69, "end": 4.86}}])
        assert config3.compute_time(version_concerto_d) == (3.96, [{0: {"start": 0, "end": 3.96}}])
        assert service3.compute_time(version_concerto_d) == (5.02, [{0: {"start": 3.96, "end": 5.02}}])
        assert config4.compute_time(version_concerto_d) == (16.38, [{0: {"start": 0, "end": 16.38}}])
        assert service4.compute_time(version_concerto_d) == (17.51, [{0: {"start": 16.38, "end": 17.51}}])

        assert in_intermediate.compute_time(version_concerto_d) == (3.2, [{0: {"start": 0, "end": 3.2}}])
        assert in_config0.compute_time(version_concerto_d) == (3.2, [{0: {"start": 3.2, "end": 3.2}}])
        assert in_config1.compute_time(version_concerto_d) == (14.07, [{0: {"start": 3.2, "end": 3.2}}])
        assert in_config2.compute_time(version_concerto_d) == (3.2, [{0: {"start": 3.2, "end": 3.2}}])
        assert in_config3.compute_time(version_concerto_d) == (3.96, [{0: {"start": 3.2, "end": 3.2}}])
        assert in_config4.compute_time(version_concerto_d) == (16.38, [{0: {"start": 3.2, "end": 3.2}}])

        assert in_intermediate0.compute_time(version_concerto_d) == (33.19, [
            {0: {"start": 3.2, "end": 3.2 + t_scs[0]}},
            {0: {"start": 14.07, "end": 14.07 + t_scs[1]}},
            {0: {"start": 3.2, "end": 3.2 + t_scs[2]}},
            {0: {"start": 3.96, "end": 3.96 + t_scs[3]}},
            {0: {"start": 16.38, "end": 16.38 + t_scs[4]}}])
        assert in_intermediate1.compute_time(version_concerto_d) == (34.59, [{0: {"start": 33.19, "end": 34.59}}])
        assert in_service0.compute_time(version_concerto_d) == (34.59, [{0: {"start": 34.59, "end": 34.59}}])
        assert in_service1.compute_time(version_concerto_d) == (34.59, [{0: {"start": 34.59, "end": 34.59}}])
        assert in_service2.compute_time(version_concerto_d) == (34.59, [{0: {"start": 34.59, "end": 34.59}}])
        assert in_service3.compute_time(version_concerto_d) == (34.59, [{0: {"start": 34.59, "end": 34.59}}])
        assert in_service4.compute_time(version_concerto_d) == (34.59, [{0: {"start": 34.59, "end": 34.59}}])
