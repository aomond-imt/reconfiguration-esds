import json

from concerto_d_model import model_time_concerto_d
from concerto_d_model.dependency_compute_model import DependencyComputeModel
from concerto_d_model.model_time_concerto_d import _compute_receive_periods_from_sending_periods, \
    count_active_intervals, count_active_intervals_sending, _compute_reconf_periods_per_node, \
    _compute_sending_periods_per_node, _get_deploy_parallel_use_case_model, compute_all_time_parameters_esds, \
    _get_update_parallel_use_case_model, _compute_uptimes_periods_per_node, compute_esds_periods


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


class TestComputeAllTimeParametersEsds:
    def test_bsn_avant(self):
        node_schedules = [
            [[0, 50]],
            [[30, 50]]
        ]
        use_0 = DependencyComputeModel("use", 0, None, [], [[15]], node_schedules)
        provide_0 = DependencyComputeModel("provide", 1, use_0, [], [[10]], node_schedules)
        use_0.connected_dep = provide_0
        list_deps = [
            use_0,
            provide_0
        ]
        all_time_parameters_esds, m, m_time, uptime_schedule = model_time_concerto_d.compute_all_time_parameters_esds(
            list_deps,
            ["use_0", "provide_0"],
            1,
            "pull",
            node_schedules,
            "sync"
        )
        assert all_time_parameters_esds == [
            {"node_id": 0, "connected_node_id": 1, "name_dep": "use_0", "type_dep": "use", "dct": 40, "trans_times": [{0: {"start": 0, "end": 15}}]},
            {"node_id": 1, "connected_node_id": 0, "name_dep": "provide_0", "type_dep": "provide", "dct": 40, "trans_times": [{0: {"start": 30, "end": 40}}]},
        ]
        assert m == m_time == 40
        assert uptime_schedule == node_schedules

    def test_bsn_apres(self):
        node_schedules = [
            [[2.52, 60]],
            [[29.34, 60]]
        ]
        use_0 = DependencyComputeModel("use", 0, None, [], [[45.12]], node_schedules)
        provide_0 = DependencyComputeModel("provide", 1, use_0, [], [[24.13]], node_schedules)
        use_0.connected_dep = provide_0
        list_deps = [
            use_0,
            provide_0
        ]
        all_time_parameters_esds, m, m_time, uptime_schedule = model_time_concerto_d.compute_all_time_parameters_esds(
            list_deps,
            ["use_0", "provide_0"],
            1,
            "pull",
            node_schedules,
            "sync"
        )
        assert all_time_parameters_esds == [
            {"node_id": 0, "connected_node_id": 1, "name_dep": "use_0", "type_dep": "use", "dct": 53.47, "trans_times": [{0: {"start": 2.52, "end": 47.64}}]},
            {"node_id": 1, "connected_node_id": 0, "name_dep": "provide_0", "type_dep": "provide", "dct": 53.47, "trans_times": [{0: {"start": 29.34, "end": 53.47}}]},
        ]
        assert m == m_time == 53.47
        assert uptime_schedule == node_schedules

    def test_bsn_next(self):
        node_schedules = [
            [[2.52, 60], [2120, 60]],
            [[29.34, 60], [2100, 60]]
        ]
        use_0 = DependencyComputeModel("use", 0, None, [], [[65]], node_schedules)
        provide_0 = DependencyComputeModel("provide", 1, use_0, [], [[10]], node_schedules)
        use_0.connected_dep = provide_0
        list_deps = [
            use_0,
            provide_0
        ]
        all_time_parameters_esds, m, m_time, uptime_schedule = model_time_concerto_d.compute_all_time_parameters_esds(
            list_deps,
            ["use_0", "provide_0"],
            1,
            "pull",
            node_schedules,
            "sync"
        )
        assert all_time_parameters_esds == [
            {"node_id": 0, "connected_node_id": 1, "name_dep": "use_0", "type_dep": "use", "dct": 2120.5, "trans_times": [{0: {"start": 2.52, "end": 67.52}}]},
            {"node_id": 1, "connected_node_id": 0, "name_dep": "provide_0", "type_dep": "provide", "dct": 39.34, "trans_times": [{0: {"start": 29.34, "end": 39.34}}]},
        ]
        assert m == m_time == 2120.5
        assert uptime_schedule == node_schedules

    def test_provide_avant(self):
        node_schedules = [
            [[23, 60], [2120, 60]],
            [[10, 60], [2100, 60]]
        ]
        use_0 = DependencyComputeModel("use", 0, None, [], [[20]], node_schedules)
        provide_0 = DependencyComputeModel("provide", 1, use_0, [], [[6]], node_schedules)
        use_0.connected_dep = provide_0
        list_deps = [
            use_0,
            provide_0
        ]
        all_time_parameters_esds, m, m_time, uptime_schedule = model_time_concerto_d.compute_all_time_parameters_esds(
            list_deps,
            ["use_0", "provide_0"],
            1,
            "pull",
            node_schedules,
            "sync"
        )
        assert all_time_parameters_esds == [
            {"node_id": 0, "connected_node_id": 1, "name_dep": "use_0", "type_dep": "use", "dct": 43, "trans_times": [{0: {"start": 23, "end": 43}}]},
            {"node_id": 1, "connected_node_id": 0, "name_dep": "provide_0", "type_dep": "provide", "dct": 16, "trans_times": [{0: {"start": 10, "end": 16}}]},
        ]
        assert m == m_time == 43
        assert uptime_schedule == node_schedules

    def test_provide_next(self):
        node_schedules = [
            [[23, 60], [2120, 60]],
            [[10, 60], [2100, 60]]
        ]
        use_0 = DependencyComputeModel("use", 0, None, [], [[21]], node_schedules)
        provide_0 = DependencyComputeModel("provide", 1, use_0, [], [[62]], node_schedules)
        use_0.connected_dep = provide_0
        list_deps = [
            use_0,
            provide_0
        ]
        all_time_parameters_esds, m, m_time, uptime_schedule = model_time_concerto_d.compute_all_time_parameters_esds(
            list_deps,
            ["use_0", "provide_0"],
            1,
            "pull",
            node_schedules,
            "sync"
        )
        assert all_time_parameters_esds == [
            {"node_id": 0, "connected_node_id": 1, "name_dep": "use_0", "type_dep": "use", "dct": 2120.5, "trans_times": [{0: {"start": 23, "end": 44}}]},
            {"node_id": 1, "connected_node_id": 0, "name_dep": "provide_0", "type_dep": "provide", "dct": 72, "trans_times": [{0: {"start": 10, "end": 72}}]},
        ]
        assert m == m_time == 2120.5
        assert uptime_schedule == node_schedules

    def test_provide_pdt(self):
        node_schedules = [
            [[23, 60], [2120, 60]],
            [[10, 60], [2100, 60]]
        ]
        use_0 = DependencyComputeModel("use", 0, None, [], [[21]], node_schedules)
        provide_0 = DependencyComputeModel("provide", 1, use_0, [], [[32, 5]], node_schedules)
        use_0.connected_dep = provide_0
        list_deps = [
            use_0,
            provide_0
        ]
        all_time_parameters_esds, m, m_time, uptime_schedule = model_time_concerto_d.compute_all_time_parameters_esds(
            list_deps,
            ["use_0", "provide_0"],
            1,
            "pull",
            node_schedules,
            "sync"
        )
        assert all_time_parameters_esds == [
            {"node_id": 0, "connected_node_id": 1, "name_dep": "use_0", "type_dep": "use", "dct": 47, "trans_times": [{0: {"start": 23, "end": 44}}]},
            {"node_id": 1, "connected_node_id": 0, "name_dep": "provide_0", "type_dep": "provide", "dct": 47, "trans_times": [{0: {"start": 10, "end": 47}}]},
        ]
        assert m == m_time == 47
        assert uptime_schedule == node_schedules

    def test_provide_overflow(self):
        node_schedules = [
            [[50, 60], [2120, 60], [4312, 60]],
            [[40, 60], [2100, 60], [4321, 60]]
        ]
        use_0 = DependencyComputeModel("use", 0, None, [], [[40, 30, 20]], node_schedules)
        use_1 = DependencyComputeModel("use", 0, None, [[use_0]], [[23]], node_schedules)
        provide_0 = DependencyComputeModel("provide", 1, use_0, [], [[10, 10, 55, 62]], node_schedules)
        provide_1 = DependencyComputeModel("provide", 1, use_1, [[provide_0]], [[12]], node_schedules)
        use_0.connected_dep = provide_0
        use_1.connected_dep = provide_1
        list_deps = [
            use_0,
            use_1,
            provide_0,
            provide_1
        ]
        all_time_parameters_esds, m, m_time, uptime_schedule = model_time_concerto_d.compute_all_time_parameters_esds(
            list_deps,
            ["use_0", "use_1", "provide_0", "provide_1"],
            1,
            "pull",
            node_schedules,
            "sync"
        )
        assert all_time_parameters_esds == [
            {"node_id": 0, "connected_node_id": 1, "name_dep": "use_0", "type_dep": "use", "dct": 4321.5, "trans_times": [{0: {"start": 50, "end": 120}, 1: {"start": 2120, "end": 2140}}]},
            {"node_id": 0, "connected_node_id": 1, "name_dep": "use_1", "type_dep": "use", "dct": 4344.5, "trans_times": [{2: {"start": 4321.5, "end": 4344.5}}]},
            {"node_id": 1, "connected_node_id": 0, "name_dep": "provide_0", "type_dep": "provide", "dct": 2162, "trans_times": [{0: {"start": 40, "end": 115}, 1: {"start": 2100, "end": 2162}}]},
            {"node_id": 1, "connected_node_id": 0, "name_dep": "provide_1", "type_dep": "provide", "dct": 4333, "trans_times": [{2: {"start": 4321, "end": 4333}}]},
        ]
        assert m == m_time == 4344.5
        assert uptime_schedule == node_schedules

    def test_deploy_5_deps(self):
        tts = {
            "server": {
                "t_sa": 30,
                "t_sc": [
                    30, 30, 30, 30, 30
                ],
                "t_sr": 30,
                "t_ss": 30,
                "t_sp": 30
            },
            "dep0": {"t_di": 30, "t_dr": 30, "t_du": 30},
            "dep1": {"t_di": 30, "t_dr": 30, "t_du": 30},
            "dep2": {"t_di": 30, "t_dr": 30, "t_du": 30},
            "dep3": {"t_di": 30, "t_dr": 30, "t_du": 30},
            "dep4": {"t_di": 30, "t_dr": 30, "t_du": 30}
        }
        nb_deps = 5
        node_schedules = [
            [(1100, 60), (2100, 60), (3100, 60), (4100, 60), (5100, 60), (6100, 60), (7100, 60), (8100, 60), (9100, 60), (10100, 60), (11150, 60), (12100, 60)],
            [(1200, 60), (2150, 60), (3200, 60), (4200, 60), (5200, 60), (6200, 60), (7150, 60), (8200, 60), (9200, 60), (10200, 60), (11120, 60), (12200, 60)],
            [(1300, 60), (2300, 60), (3300, 60), (4300, 60), (5080, 60), (6300, 60), (7080, 60), (8300, 60), (9300, 60), (10300, 60), (11130, 60), (12300, 60)],
            [(1400, 60), (2400, 60), (3400, 60), (4400, 60), (5130, 60), (6400, 60), (7200, 60), (8103, 60), (9400, 60), (10400, 60), (11400, 60), (12400, 60)],
            [(1500, 60), (2500, 60), (3500, 60), (4500, 60), (5500, 60), (6100, 60), (7500, 60), (8102, 60), (9500, 60), (10500, 60), (11500, 60), (12500, 60)],
            [(1600, 60), (2600, 60), (3600, 60), (4600, 60), (5600, 60), (6100.5, 60), (7600, 60), (8101, 60), (9600, 60), (10600, 60), (11600, 60), (12600, 60)]
        ]
        list_deps, name_deps = _get_deploy_parallel_use_case_model(tts, nb_deps)

        all_time_parameters_esds, m, m_time, uptime_schedule = model_time_concerto_d.compute_all_time_parameters_esds(
            list_deps,
            name_deps,
            5,
            "pull",
            node_schedules,
            "sync"
        )
        assert all_time_parameters_esds == [
            {'node_id': 1, 'connected_node_id': 0, 'name_dep': 'config0', 'type_dep': 'provide', 'dct': 1230, 'trans_times': [{0: {'start': 1200, 'end': 1230}}]},
            {'node_id': 2, 'connected_node_id': 0, 'name_dep': 'config1', 'type_dep': 'provide', 'dct': 1330, 'trans_times': [{0: {'start': 1300, 'end': 1330}}]},
            {'node_id': 3, 'connected_node_id': 0, 'name_dep': 'config2', 'type_dep': 'provide', 'dct': 1430, 'trans_times': [{0: {'start': 1400, 'end': 1430}}]},
            {'node_id': 4, 'connected_node_id': 0, 'name_dep': 'config3', 'type_dep': 'provide', 'dct': 1530, 'trans_times': [{0: {'start': 1500, 'end': 1530}}]},
            {'node_id': 5, 'connected_node_id': 0, 'name_dep': 'config4', 'type_dep': 'provide', 'dct': 1630, 'trans_times': [{0: {'start': 1600, 'end': 1630}}]},
            {'node_id': 1, 'connected_node_id': 0, 'name_dep': 'service0', 'type_dep': 'provide', 'dct': 1260, 'trans_times': [{0: {'start': 1230, 'end': 1260}}]},
            {'node_id': 2, 'connected_node_id': 0, 'name_dep': 'service1', 'type_dep': 'provide', 'dct': 1360, 'trans_times': [{0: {'start': 1330, 'end': 1360}}]},
            {'node_id': 3, 'connected_node_id': 0, 'name_dep': 'service2', 'type_dep': 'provide', 'dct': 1460, 'trans_times': [{0: {'start': 1430, 'end': 1460}}]},
            {'node_id': 4, 'connected_node_id': 0, 'name_dep': 'service3', 'type_dep': 'provide', 'dct': 1560, 'trans_times': [{0: {'start': 1530, 'end': 1560}}]},
            {'node_id': 5, 'connected_node_id': 0, 'name_dep': 'service4', 'type_dep': 'provide', 'dct': 1660, 'trans_times': [{0: {'start': 1630, 'end': 1660}}]},
            {'node_id': 0, 'connected_node_id': None, 'name_dep': 'in_intermediate', 'type_dep': 'intermediate', 'dct': 1130, 'trans_times': [{0: {'start': 1100, 'end': 1130}}]},
            {'node_id': 0, 'connected_node_id': 1, 'name_dep': 'in_config0', 'type_dep': 'use', 'dct': 2150.5, 'trans_times': [{0: {'start': 1130, 'end': 1130}}]},
            {'node_id': 0, 'connected_node_id': 2, 'name_dep': 'in_config1', 'type_dep': 'use', 'dct': 5100.5, 'trans_times': [{0: {'start': 1130, 'end': 1130}}]},
            {'node_id': 0, 'connected_node_id': 3, 'name_dep': 'in_config2', 'type_dep': 'use', 'dct': 5130.5, 'trans_times': [{0: {'start': 1130, 'end': 1130}}]},
            {'node_id': 0, 'connected_node_id': 4, 'name_dep': 'in_config3', 'type_dep': 'use', 'dct': 6100.5, 'trans_times': [{0: {'start': 1130, 'end': 1130}}]},
            {'node_id': 0, 'connected_node_id': 5, 'name_dep': 'in_config4', 'type_dep': 'use', 'dct': 6101,   'trans_times': [{0: {'start': 1130, 'end': 1130}}]},
            {'node_id': 0, 'connected_node_id': None, 'name_dep': 'in_intermediate0', 'type_dep': 'intermediate', 'dct': 6131, 'trans_times': [{1: {'start': 2150.5, 'end': 2180.5}}, {4: {'start': 5100.5, 'end': 5130.5}}, {4: {'start': 5130.5, 'end': 5160.5}}, {5: {'start': 6100.5, 'end': 6130.5}}, {5: {'start': 6101, 'end': 6131}}]},
            {'node_id': 0, 'connected_node_id': None, 'name_dep': 'in_intermediate1', 'type_dep': 'intermediate', 'dct': 6161, 'trans_times': [{5: {'start': 6131, 'end': 6161}}]},
            {'node_id': 0, 'connected_node_id': 1, 'name_dep': 'in_service0', 'type_dep': 'use', 'dct': 7150.5, 'trans_times': [{6: {'start': 7100, 'end': 7100}}]},
            {'node_id': 0, 'connected_node_id': 2, 'name_dep': 'in_service1', 'type_dep': 'use', 'dct': 7100.5, 'trans_times': [{6: {'start': 7100, 'end': 7100}}]},
            {'node_id': 0, 'connected_node_id': 3, 'name_dep': 'in_service2', 'type_dep': 'use', 'dct': 8103.5, 'trans_times': [{6: {'start': 7100, 'end': 7100}}]},
            {'node_id': 0, 'connected_node_id': 4, 'name_dep': 'in_service3', 'type_dep': 'use', 'dct': 8102.5, 'trans_times': [{6: {'start': 7100, 'end': 7100}}]},
            {'node_id': 0, 'connected_node_id': 5, 'name_dep': 'in_service4', 'type_dep': 'use', 'dct': 8101.5, 'trans_times': [{6: {'start': 7100, 'end': 7100}}]},
        ]
        assert m == m_time == 8103.5
        assert uptime_schedule == node_schedules

        # Test uptimes generated
        expe_parameters, title = compute_esds_periods(all_time_parameters_esds, m, m_time, "test", 5, "test", tts, "pull", uptime_schedule, "sync")
        duration = uptime_schedule[0][0][1]
        assert expe_parameters["uptimes_periods_per_node"] == {
            0: [[1100, 1100 + 60], [2100, 2100 + 60], [3100, 3100 + 60], [4100, 4100 + 60], [5100, 5100 + 60], [6100, 6100 + 60], [7100, 7100 + 60], [8100, 8103.5]],
            1: [[1200, 1200 + 60], [2150, 2150 + 60], [3200, 3200 + 60], [4200, 4200 + 60], [5200, 5200 + 60], [6200, 6200 + 60], [7150, 7150 + 60]],
            2: [[1300, 1300 + 60], [2300, 2300 + 60], [3300, 3300 + 60], [4300, 4300 + 60], [5080, 5080 + 60], [6300, 6300 + 60], [7080, 7080 + 60]],
            3: [[1400, 1400 + 60], [2400, 2400 + 60], [3400, 3400 + 60], [4400, 4400 + 60], [5130, 5130 + 60], [6400, 6400 + 60], [7200, 7200 + 60], [8103, 8103.5]],
            4: [[1500, 1500 + 60], [2500, 2500 + 60], [3500, 3500 + 60], [4500, 4500 + 60], [5500, 5500 + 60], [6100, 6100 + 60], [7500, 7500 + 60], [8102, 8103.5]],
            5: [[1600, 1600 + 60], [2600, 2600 + 60], [3600, 3600 + 60], [4600, 4600 + 60], [5600, 5600 + 60], [6100.5, 6100.5 + 60], [7600, 7600 + 60], [8101, 8103.5]],
            6: []
        }
        assert expe_parameters["reconf_periods_per_node"] == {
            0: [[1100, 1130, 1], [1130, 2150.5, 0], [2150.5, 2180.5, 1], [2180.5, 5100.5, 0], [5100.5, 5130.5, 1], [5130.5, 5160.5, 1], [5160.5, 6100.5, 0], [6100.5, 6101, 1], [6101, 6130.5, 2], [6130.5, 6131, 1], [6131, 6161, 1]],
            1: [[1200, 1230, 1], [1230, 1260, 1]],
            2: [[1300, 1330, 1], [1330, 1360, 1]],
            3: [[1400, 1430, 1], [1430, 1460, 1]],
            4: [[1500, 1530, 1], [1530, 1560, 1]],
            5: [[1600, 1630, 1], [1630, 1660, 1]],
            6: []
        }

    def test_update_5_deps(self):
        tts = {
            "server": {
                "t_sa": 30,
                "t_sc": [
                    30, 30, 30, 30, 30
                ],
                "t_sr": 30,
                "t_ss": [
                    30, 30, 30, 30, 30
                ],
                "t_sp": [
                    30, 30, 30, 30, 30
                ]
            },
            "dep0": {"t_di": 30, "t_dr": 5, "t_du": 2},
            "dep1": {"t_di": 30, "t_dr": 30, "t_du": 30},
            "dep2": {"t_di": 30, "t_dr": 30, "t_du": 30},
            "dep3": {"t_di": 30, "t_dr": 30, "t_du": 30},
            "dep4": {"t_di": 30, "t_dr": 30, "t_du": 30}
        }
        nb_deps = 5
        node_schedules = [
            [(1100, 60), (2100, 60), (3100, 60), (4100, 60), (5100, 60), (6100, 60), (7100, 60), (8100, 60), (9100, 60), (10100, 60), (11150, 60), (12100, 60)],
            [(1200, 60), (2150, 60), (3200, 60), (4200, 60), (5200, 60), (6200, 60), (7150, 60), (8200, 60), (9200, 60), (10200, 60), (11120, 60), (12200, 60)],
            [(1300, 60), (2300, 60), (3300, 60), (4300, 60), (5080, 60), (6300, 60), (7080, 60), (8300, 60), (9300, 60), (10300, 60), (11130, 60), (12300, 60)],
            [(1400, 60), (2400, 60), (3400, 60), (4400, 60), (5130, 60), (6400, 60), (7200, 60), (8103, 60), (9400, 60), (10400, 60), (11400, 60), (12400, 60)],
            [(1500, 60), (2500, 60), (3500, 60), (4500, 60), (5500, 60), (6100, 60), (7500, 60), (8102, 60), (9500, 60), (10500, 60), (11500, 60), (12500, 60)],
            [(1600, 60), (2600, 60), (3600, 60), (4600, 60), (5600, 60), (6100.5, 60), (7600, 60), (8101, 60), (9600, 60), (10600, 60), (11600, 60), (12600, 60)]
        ]
        list_deps, name_deps = _get_update_parallel_use_case_model(tts, nb_deps)

        all_time_parameters_esds, m, m_time, uptime_schedule = model_time_concerto_d.compute_all_time_parameters_esds(
            list_deps,
            name_deps,
            5,
            "pull",
            node_schedules,
            "sync"
        )
        assert all_time_parameters_esds == [
            {'node_id': 1, 'connected_node_id': 0, 'name_dep': 'update_in_suspend_0', 'type_dep': 'use', 'dct': 2150.5, 'trans_times': [{0: {'start': 1200, 'end': 1200}}]},
            {'node_id': 2, 'connected_node_id': 0, 'name_dep': 'update_in_suspend_1', 'type_dep': 'use', 'dct': 5100.5, 'trans_times': [{0: {'start': 1300, 'end': 1300}}]},
            {'node_id': 3, 'connected_node_id': 0, 'name_dep': 'update_in_suspend_2', 'type_dep': 'use', 'dct': 5130.5, 'trans_times': [{0: {'start': 1400, 'end': 1400}}]},
            {'node_id': 4, 'connected_node_id': 0, 'name_dep': 'update_in_suspend_3', 'type_dep': 'use', 'dct': 6100.5, 'trans_times': [{0: {'start': 1500, 'end': 1500}}]},
            {'node_id': 5, 'connected_node_id': 0, 'name_dep': 'update_in_suspend_4', 'type_dep': 'use', 'dct': 6101.0, 'trans_times': [{0: {'start': 1600, 'end': 1600}}]},
            {'node_id': 1, 'connected_node_id': 0, 'name_dep': 'update_service_0', 'type_dep': 'provide', 'dct': 2157.5, 'trans_times': [{1: {'start': 2150.5, 'end': 2157.5}}]},
            {'node_id': 2, 'connected_node_id': 0, 'name_dep': 'update_service_1', 'type_dep': 'provide', 'dct': 5160.5, 'trans_times': [{4: {'start': 5100.5, 'end': 5160.5}}]},
            {'node_id': 3, 'connected_node_id': 0, 'name_dep': 'update_service_2', 'type_dep': 'provide', 'dct': 5190.5, 'trans_times': [{4: {'start': 5130.5, 'end': 5190.5}}]},
            {'node_id': 4, 'connected_node_id': 0, 'name_dep': 'update_service_3', 'type_dep': 'provide', 'dct': 6160.5, 'trans_times': [{5: {'start': 6100.5, 'end': 6160.5}}]},
            {'node_id': 5, 'connected_node_id': 0, 'name_dep': 'update_service_4', 'type_dep': 'provide', 'dct': 6161.0, 'trans_times': [{5: {'start': 6101.0, 'end': 6161.0}}]},
            {'node_id': 0, 'connected_node_id': 1, 'name_dep': 'update_out_suspend_0', 'type_dep': 'provide', 'dct': 1130, 'trans_times': [{0: {'start': 1100, 'end': 1130}}]},
            {'node_id': 0, 'connected_node_id': 2, 'name_dep': 'update_out_suspend_1', 'type_dep': 'provide', 'dct': 1130, 'trans_times': [{0: {'start': 1100, 'end': 1130}}]},
            {'node_id': 0, 'connected_node_id': 3, 'name_dep': 'update_out_suspend_2', 'type_dep': 'provide', 'dct': 1130, 'trans_times': [{0: {'start': 1100, 'end': 1130}}]},
            {'node_id': 0, 'connected_node_id': 4, 'name_dep': 'update_out_suspend_3', 'type_dep': 'provide', 'dct': 1130, 'trans_times': [{0: {'start': 1100, 'end': 1130}}]},
            {'node_id': 0, 'connected_node_id': 5, 'name_dep': 'update_out_suspend_4', 'type_dep': 'provide', 'dct': 1130, 'trans_times': [{0: {'start': 1100, 'end': 1130}}]},
            {'node_id': 0, 'connected_node_id': None, 'name_dep': 'intermediate_configured', 'type_dep': 'intermediate', 'dct': 1160, 'trans_times': [{0: {'start': 1130, 'end': 1160}}, {0: {'start': 1130, 'end': 1160}}, {0: {'start': 1130, 'end': 1160}}, {0: {'start': 1130, 'end': 1160}}, {0: {'start': 1130, 'end': 1160}}]},
            {'node_id': 0, 'connected_node_id': 1, 'name_dep': 'update_in_configured_0', 'type_dep': 'use', 'dct': 2157.5, 'trans_times': [{0: {'start': 1160, 'end': 1160}, 1: {'start': 2100, 'end': 2100}}]},
            {'node_id': 0, 'connected_node_id': 2, 'name_dep': 'update_in_configured_1', 'type_dep': 'use', 'dct': 7100.5, 'trans_times': [{0: {'start': 1160, 'end': 1160}, 1: {'start': 2100, 'end': 2100}}]},
            {'node_id': 0, 'connected_node_id': 3, 'name_dep': 'update_in_configured_2', 'type_dep': 'use', 'dct': 8103.5, 'trans_times': [{0: {'start': 1160, 'end': 1160}, 1: {'start': 2100, 'end': 2100}}]},
            {'node_id': 0, 'connected_node_id': 4, 'name_dep': 'update_in_configured_3', 'type_dep': 'use', 'dct': 8102.5, 'trans_times': [{0: {'start': 1160, 'end': 1160}, 1: {'start': 2100, 'end': 2100}}]},
            {'node_id': 0, 'connected_node_id': 5, 'name_dep': 'update_in_configured_4', 'type_dep': 'use', 'dct': 8101.5, 'trans_times': [{0: {'start': 1160, 'end': 1160}, 1: {'start': 2100, 'end': 2100}}]},
            {'node_id': 0, 'connected_node_id': None, 'name_dep': 'wait_all_true', 'type_dep': 'intermediate', 'dct': 8103.5, 'trans_times': [{1: {'start': 2157.5, 'end': 2157.5}}, {6: {'start': 7100.5, 'end': 7100.5}}, {7: {'start': 8103.5, 'end': 8103.5}}, {7: {'start': 8102.5, 'end': 8102.5}}, {7: {'start': 8101.5, 'end': 8101.5}}]},
            {'node_id': 0, 'connected_node_id': None, 'name_dep': 'update_service', 'type_dep': 'intermediate', 'dct': 8133.5, 'trans_times': [{7: {'start': 8103.5, 'end': 8133.5}}]},
        ]
        assert m == m_time == 8133.5
        assert uptime_schedule == node_schedules

