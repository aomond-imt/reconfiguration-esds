from concerto_d_time_computation.dependency_compute_model import get_next_overlap, DependencyComputeModel


class TestGetNextOverlap:
    def test_get_next_information_time_start_after_schedule(self):
        node_schedule = [
            [[0, 1]],
            [[0, 1]]
        ]

        next_overlap_0 = get_next_overlap(0, 0, 1, node_schedule, "sync")
        next_overlap_1 = get_next_overlap(15, 0, 1, node_schedule, "sync")
        next_overlap_2 = get_next_overlap(60, 0, 1, node_schedule, "sync")

        assert next_overlap_0 == 0
        assert next_overlap_1 == 15
        assert next_overlap_2 is None


    def test_get_next_information_time_start_before_uptimes(self):
        node_schedule = [
            [[0, 1], [150, 1]],
            [[0, 1], [120, 1]]
        ]

        next_overlap_3 = get_next_overlap(30, 0, 1, node_schedule, "sync")
        next_overlap_4 = get_next_overlap(60, 0, 1, node_schedule, "sync")
        next_overlap_5 = get_next_overlap(155, 0, 1, node_schedule, "sync")

        assert next_overlap_3 == 30
        assert next_overlap_4 == 150
        assert next_overlap_5 == 155


    def test_get_next_information_skip_sleep_rounds(self):
        node_schedule = [
            [[-1, -1], [0, 1], [-1, -1], [120, 1], [190, 1], [-1, -1]],
            [[-1, -1], [-1, -1], [60, 1], [-1, -1], [200, 1], [-1, -1]]
        ]

        next_overlap_6 = get_next_overlap(100, 0, 1, node_schedule, "sync")
        next_overlap_7 = get_next_overlap(30, 0, 1, node_schedule, "sync")
        next_overlap_8 = get_next_overlap(260, 0, 1, node_schedule, "sync")
        next_overlap_9 = get_next_overlap(0, 0, 1, node_schedule, "sync")

        assert next_overlap_6 == 200
        assert next_overlap_7 == 200
        assert next_overlap_8 is None
        assert next_overlap_9 == 200


class TestDependencyComputeModel:
    def test_simple_deploy_1(self):
        no_sleeping_nodes_schedules = [
            [[0, 1]],
            [[0, 1]]
        ]
        provide = DependencyComputeModel("provide", 0, None, [], [[2]], no_sleeping_nodes_schedules)
        use = DependencyComputeModel("use", 1, provide, [], [[3]], no_sleeping_nodes_schedules)
        provide.connected_dep = use

        version_concerto_d = "sync"
        assert provide.compute_time(version_concerto_d) == (2, [{0: {"start": 0, "end": 2}}])
        assert use.compute_time(version_concerto_d) == (3, [{0: {"start": 0, "end": 3}}])


    def test_simple_deploy_2(self):
        no_sleeping_nodes_schedules = [
            [[0, 1]],
            [[0, 1]],
            [[0, 1]],
            [[0, 1]],
            [[0, 1]],
            [[0, 1]],
        ]

        # a
        pa0 = DependencyComputeModel("provide", 0, None, [], [[17]], no_sleeping_nodes_schedules)

        # b
        pb0 = DependencyComputeModel("provide", 1, None, [], [[10]], no_sleeping_nodes_schedules)
        ub0 = DependencyComputeModel("use", 1, None, [], [[7]], no_sleeping_nodes_schedules)
        pb1 = DependencyComputeModel("provide", 1, None, [[ub0]], [[8]], no_sleeping_nodes_schedules)

        # c
        uc0 = DependencyComputeModel("use", 2, None, [], [[3]], no_sleeping_nodes_schedules)
        pc0 = DependencyComputeModel("provide", 2, None, [[uc0]], [[6]], no_sleeping_nodes_schedules)
        uc1 = DependencyComputeModel("use", 2, None, [[uc0]], [[15]], no_sleeping_nodes_schedules)
        uc2 = DependencyComputeModel("use", 2, None, [[uc0]], [[16]], no_sleeping_nodes_schedules)
        pc1 = DependencyComputeModel("provide", 2, None, [[uc0], [uc2]], [[0]], no_sleeping_nodes_schedules)
        pc2 = DependencyComputeModel("provide", 2, None, [[uc0], [uc1, uc2]], [[22], [13]], no_sleeping_nodes_schedules)

        # d
        ud0 = DependencyComputeModel("use", 3, None, [], [[20]], no_sleeping_nodes_schedules)
        ud1 = DependencyComputeModel("use", 3, None, [[ud0]], [[5]], no_sleeping_nodes_schedules)

        # e
        ue0 = DependencyComputeModel("use", 4, None, [], [[14]], no_sleeping_nodes_schedules)

        # f
        pf0 = DependencyComputeModel("provide", 5, None, [], [[15]], no_sleeping_nodes_schedules)

        # associations
        pa0.connected_dep = ub0
        ub0.connected_dep = pa0

        pb0.connected_dep = uc0
        uc0.connected_dep = pb0

        pb1.connected_dep = uc1
        uc1.connected_dep = pb1

        pc0.connected_dep = ud0
        ud0.connected_dep = pc0

        pc1.connected_dep = ud1
        ud1.connected_dep = pc1

        uc2.connected_dep = pf0
        pf0.connected_dep = uc2

        pc2.connected_dep = ue0
        ue0.connected_dep = pc2

        version_concerto_d = "sync"
        # a
        assert pa0.compute_time(version_concerto_d) == (17, [{0: {"start": 0, "end": 17}}])

        # b
        assert pb0.compute_time(version_concerto_d) == (10, [{0: {"start": 0, "end": 10}}])
        assert ub0.compute_time(version_concerto_d) == (17, [{0: {"start": 0, "end": 7}}])
        assert pb1.compute_time(version_concerto_d) == (25, [{0: {"start": 17, "end": 25}}])

        # c
        assert uc0.compute_time(version_concerto_d) == (10, [{0: {"start": 0, "end": 3}}])
        assert pc0.compute_time(version_concerto_d) == (16, [{0: {"start": 10, "end": 16}}])
        assert uc1.compute_time(version_concerto_d) == (25, [{0: {"start": 10, "end": 25}}])
        assert uc2.compute_time(version_concerto_d) == (26, [{0: {"start": 10, "end": 26}}])
        assert pc1.compute_time(version_concerto_d) == (26, [{0: {"start": 26, "end": 26}}])
        assert pc2.compute_time(version_concerto_d) == (47, [{0: {"start": 25, "end": 47}}, {0: {"start": 26, "end": 39}}])

        # d
        assert ud0.compute_time(version_concerto_d) == (20, [{0: {"start": 0, "end": 20}}])
        assert ud1.compute_time(version_concerto_d) == (26, [{0: {"start": 20, "end": 25}}])

        # e
        assert ue0.compute_time(version_concerto_d) == (47, [{0: {"start": 0, "end": 14}}])

        # f
        assert pf0.compute_time(version_concerto_d) == (15, [{0: {"start": 0, "end": 15}}])


    def test_deploy_multiple_conn_2_deps(self):
        node_schedule = [
            [[0, 1], [100, 1]],
            [[0, 1], [100, 1]],
        ]
        provide_1 = DependencyComputeModel("provide", 0, None, [], [[10]], node_schedule)
        provide_2 = DependencyComputeModel("provide", 0, None, [[provide_1]], [[15]], node_schedule)
        provide_3 = DependencyComputeModel("provide", 0, None, [[provide_2]], [[20]], node_schedule)
        provide_4 = DependencyComputeModel("provide", 0, None, [[provide_3]], [[35]], node_schedule)
        use_1 = DependencyComputeModel("use", 1, None, [], [[5]], node_schedule)
        use_2 = DependencyComputeModel("use", 1, None, [[use_1]], [[20]], node_schedule)
        use_3 = DependencyComputeModel("use", 1, None, [[use_2]], [[39]], node_schedule)
        use_4 = DependencyComputeModel("use", 1, None, [[use_3]], [[25]], node_schedule)
        use_1.connected_dep = provide_1
        provide_1.connected_dep = use_1
        use_2.connected_dep = provide_2
        provide_2.connected_dep = use_2
        use_3.connected_dep = provide_3
        provide_3.connected_dep = use_3
        use_4.connected_dep = provide_4
        provide_4.connected_dep = use_4

        version_concerto_d = "sync"
        assert provide_1.compute_time(version_concerto_d) == (10, [{0: {"start": 0, "end": 10}}])
        assert provide_2.compute_time(version_concerto_d) == (25, [{0: {"start": 10, "end": 25}}])
        assert provide_3.compute_time(version_concerto_d) == (45, [{0: {"start": 25, "end": 45}}])
        assert provide_4.compute_time(version_concerto_d) == (80, [{0: {"start": 45, "end": 80}}])

        assert use_1.compute_time(version_concerto_d) == (10, [{0: {"start": 0, "end": 5}}])
        assert use_2.compute_time(version_concerto_d) == (30, [{0: {"start": 10, "end": 30}}])
        assert use_3.compute_time(version_concerto_d) == (100, [{0: {"start": 30, "end": 69}}])
        assert use_4.compute_time(version_concerto_d) == (125, [{1: {"start": 100, "end": 125}}])


def test_parallel_uses():
    print()
    schedule = [
        [[0, 1], [160, 1], [-1, -1]],
        [[0, 1], [115, 1], [-1, -1]],
        [[0, 1], [115, 1], [-1, -1]],
    ]
    config_0 = DependencyComputeModel("provide", 1, None, [], [[49]], schedule)
    config_1 = DependencyComputeModel("provide", 1, None, [], [[49]], schedule)
    service_0 = DependencyComputeModel("provide", 2, None, [], [[52]], schedule)
    service_1 = DependencyComputeModel("provide", 2, None, [], [[52]], schedule)

    in_config_0 = DependencyComputeModel("use", 0, None, [], [[0]], schedule)
    in_config_1 = DependencyComputeModel("use", 0, None, [], [[0]], schedule)
    in_service_0 = DependencyComputeModel("use", 0, None, [[in_config_0, in_config_1]], [[22 + 3.4], [10 + 3.4]], schedule)
    in_service_1 = DependencyComputeModel("use", 0, None, [[in_config_0, in_config_1]], [[22 + 3.4], [10 + 3.4]], schedule)

    config_0.connected_dep = in_config_0
    in_config_0.connected_dep = config_0
    config_1.connected_dep = in_config_1
    in_config_1.connected_dep = config_1
    config_0.connected_dep = in_config_0
    in_config_0.connected_dep = config_0
    config_0.connected_dep = in_config_0
    in_config_0.connected_dep = config_0

    service_0.connected_dep = in_service_0
    in_service_0.connected_dep = service_0
    service_1.connected_dep = in_service_1
    in_service_1.connected_dep = service_1
    service_0.connected_dep = in_service_0
    in_service_0.connected_dep = service_0
    service_0.connected_dep = in_service_0
    in_service_0.connected_dep = service_0

    version_concerto_d = "sync"
    for dep in [config_0, config_1, service_0, service_1, in_config_0, in_config_1, in_service_0, in_service_1]:
        print(dep.compute_time(version_concerto_d))


class TestUseDependency:
    def test_compute_lp_time_end_1(self):
        all_trans = [20, 30, 15, 18]
        nodes_schedules = [
            [[20, 1], [100, 1]]
        ]
        use_dep = DependencyComputeModel("use", 0, None, [], [all_trans])
        use_dep.nodes_schedules = nodes_schedules
        result, l = use_dep._compute_time_lp_end(all_trans, 20, 0)

        assert result == 133
        assert l == {0: {"start": 20, "end": 70}, 1: {"start": 100, "end": 133}}

    def test_compute_lp_time_end_2(self):
        all_trans = [20, 35, 15, 18, 30, 45]
        nodes_schedules = [
            [[10, 1], [100, 1], [190, 0], [400, 0]]
        ]
        use_dep = DependencyComputeModel("use", 0, None, [], [all_trans])
        use_dep.nodes_schedules = nodes_schedules
        result, l = use_dep._compute_time_lp_end(all_trans, 10, 0)

        assert result == 235
        assert l == {0: {"start": 10, "end": 65}, 1: {"start": 100, "end": 163}, 2: {"start": 190, "end": 235}}

    def test_compute_lp_time_end_3(self):
        all_trans = [30, 15, 20, 0]
        nodes_schedules = [
            [[10, 1], [100, 1]]
        ]
        use_dep = DependencyComputeModel("use", 0, None, [], [all_trans])
        use_dep.nodes_schedules = nodes_schedules
        result, l = use_dep._compute_time_lp_end(all_trans, 34.4, 0)

        assert result == 135
        assert l == {0: {"start": 34.4, "end": 64.4}, 1: {"start": 100, "end": 135}}

    def test_compute_time_1(self):
        all_trans_use = [30, 25, 20.3, 0]
        all_trans_provide = [30, 25, 20.3, 0]
        nodes_schedules = [
            [[10, 1], [100, 1]],
            [[10, 1], [100, 1]]
        ]

        use_dep = DependencyComputeModel("use", 0, None, [], [all_trans_use])
        use_dep.nodes_schedules = nodes_schedules
        provide_dep = DependencyComputeModel("provide", 1, None, [], [all_trans_provide])
        provide_dep.nodes_schedules = nodes_schedules
        use_dep.connected_dep = provide_dep
        provide_dep.connected_dep = provide_dep

        version_concerto_d = "sync"
        use_time, use_results = use_dep.compute_time(version_concerto_d)
        provide_time, provide_results = provide_dep.compute_time(version_concerto_d)

        assert use_time == 120.3
        assert use_results == [{0: {"start": 10, "end": 65}, 1: {"start": 100, "end": 120.3}}]
        assert provide_time == 120.3
        assert provide_results == [{0: {"start": 10, "end": 65}, 1: {"start": 100, "end": 120.3}}]


class TestParallelismNoDeps:
    def test_1(self):
        nodes_schedules = [
            [[10, 1]]
        ]
        intermediate_0 = DependencyComputeModel("intermediate", 0, None, [], [[5]], nodes_schedules)
        intermediate_1 = DependencyComputeModel("intermediate", 0, None, [[intermediate_0]], [[6]], nodes_schedules)
        intermediate_2 = DependencyComputeModel("intermediate", 0, None, [[intermediate_0]], [[4]], nodes_schedules)
        intermediate_3 = DependencyComputeModel("intermediate", 0, None, [], [[10]], nodes_schedules)

        version_concerto_d = "sync"
        assert intermediate_0.compute_time(version_concerto_d) == (15, [{0: {"start": 10, "end": 15}}])
        assert intermediate_1.compute_time(version_concerto_d) == (21, [{0: {"start": 15, "end": 21}}])
        assert intermediate_2.compute_time(version_concerto_d) == (19, [{0: {"start": 15, "end": 19}}])
        assert intermediate_3.compute_time(version_concerto_d) == (20, [{0: {"start": 10, "end": 20}}])


class TestUseProvide:
    def test_1(self):
        nodes_schedules = [
            [[10, 1]],
            [[10, 1]],
        ]
        provide_0 = DependencyComputeModel("provide", 0, None, [], [[5]], nodes_schedules)
        intermediate_1 = DependencyComputeModel("intermediate", 0, None, [[provide_0]], [[6]], nodes_schedules)
        intermediate_2 = DependencyComputeModel("intermediate", 0, None, [[provide_0]], [[4]], nodes_schedules)
        intermediate_3 = DependencyComputeModel("intermediate", 0, None, [], [[10]], nodes_schedules)
        provide_1 = DependencyComputeModel("provide", 0, None, [[intermediate_1, intermediate_2, intermediate_3]], [[0], [0], [0]], nodes_schedules)

        use_0 = DependencyComputeModel("use", 1, None, [], [[7]], nodes_schedules)
        use_1 = DependencyComputeModel("use", 1, None, [[use_0]], [[5]], nodes_schedules)

        provide_0.connected_dep = use_0
        use_0.connected_dep = provide_0
        provide_1.connected_dep = use_1
        use_1.connected_dep = provide_1

        version_concerto_d = "sync"
        assert provide_0.compute_time(version_concerto_d) == (15, [{0: {"start": 10, "end": 15}}])
        assert intermediate_1.compute_time(version_concerto_d) == (21, [{0: {"start": 15, "end": 21}}])
        assert intermediate_2.compute_time(version_concerto_d) == (19, [{0: {"start": 15, "end": 19}}])
        assert intermediate_3.compute_time(version_concerto_d) == (20, [{0: {"start": 10, "end": 20}}])
        assert provide_1.compute_time(version_concerto_d) == (21, [{0: {"start": 21, "end": 21}}, {0: {"start": 19, "end": 19}}, {0: {"start": 20, "end": 20}}])

        assert use_0.compute_time(version_concerto_d) == (17, [{0: {"start": 10, "end": 17}}])
        assert use_1.compute_time(version_concerto_d) == (22, [{0: {"start": 17, "end": 22}}])


class TestUptimeSchedules:
    provide_0 = DependencyComputeModel("provide", 1, None, [], [[1]])
    provide_1 = DependencyComputeModel("provide", 2, None, [], [[1]])

    use_0 = DependencyComputeModel("use", 0, None, [], [[10]])
    use_1 = DependencyComputeModel("use", 0, None, [], [[1]])
    intermediate_0 = DependencyComputeModel("intermediate", 0, None, [[use_0, use_1]], [[10], [1]])

    provide_0.connected_dep = use_0
    use_0.connected_dep = provide_0
    provide_1.connected_dep = use_1
    use_1.connected_dep = provide_1

    def test_1(self):
        nodes_schedules = [
            [[0, 1]],
            [[0, 1]],
            [[0, 1]]
        ]

        self.provide_0.nodes_schedules = nodes_schedules
        self.provide_1.nodes_schedules = nodes_schedules
        self.use_0.nodes_schedules = nodes_schedules
        self.use_1.nodes_schedules = nodes_schedules
        self.intermediate_0.nodes_schedules = nodes_schedules

        version_concerto_d = "sync"
        assert self.intermediate_0.compute_time(version_concerto_d) == (20, [{0: {"start": 10, "end": 20}}, {0: {"start": 1, "end": 2}}])
        version_concerto_d = "async"
        assert self.intermediate_0.compute_time(version_concerto_d) == (20, [{0: {"start": 10, "end": 20}}, {0: {"start": 1, "end": 2}}])

    def test_2(self):
        nodes_schedules = [
            [[0, 1]],
            [[0, 1]],
            [[40, 1]]
        ]

        self.provide_0.nodes_schedules = nodes_schedules
        self.provide_1.nodes_schedules = nodes_schedules
        self.use_0.nodes_schedules = nodes_schedules
        self.use_1.nodes_schedules = nodes_schedules
        self.intermediate_0.nodes_schedules = nodes_schedules

        version_concerto_d = "sync"
        assert self.intermediate_0.compute_time(version_concerto_d) == (42, [{0: {"start": 10, "end": 20}}, {0: {"start": 41, "end": 42}}])
        version_concerto_d = "async"
        assert self.intermediate_0.compute_time(version_concerto_d) == (42, [{0: {"start": 10, "end": 20}}, {0: {"start": 41, "end": 42}}])

    def test_3(self):
        nodes_schedules = [
            [[51, 1], [105, 1]],
            [[0, 1], [105, 1]],
            [[0, 1], [105, 1]]
        ]

        self.provide_0.nodes_schedules = nodes_schedules
        self.provide_1.nodes_schedules = nodes_schedules
        self.use_0.nodes_schedules = nodes_schedules
        self.use_1.nodes_schedules = nodes_schedules
        self.intermediate_0.nodes_schedules = nodes_schedules

        version_concerto_d = "sync"
        assert self.intermediate_0.compute_time(version_concerto_d) == (115, [{1: {"start": 105, "end": 115}}, {1: {"start": 105, "end": 106}}])
        version_concerto_d = "async"
        assert self.intermediate_0.compute_time(version_concerto_d) == (71, [{0: {"start": 61, "end": 71}}, {0: {"start": 52, "end": 53}}])
