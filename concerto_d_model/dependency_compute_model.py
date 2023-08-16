from typing import List


def get_next_overlap(time_start: float, num_node_a: int, num_node_b: int, nodes_schedule: List, version: str, duration: float = 60):
    schedule_a = nodes_schedule[num_node_a]
    schedule_b = nodes_schedule[num_node_b]
    offset_polling = 0.5  # Worst case for contact between nodes due to wait between 2 pings

    if version == "sync":
        for item_a, item_b in zip(schedule_a, schedule_b):
            uptime_a, _ = item_a
            uptime_b, _ = item_b

            if uptime_a == -1 or uptime_b == -1:
                continue
            start_overlap = max(uptime_a, uptime_b)
            overlap_duration = min(uptime_a+duration, uptime_b+duration) - start_overlap
            if overlap_duration > 0 and time_start + offset_polling <= start_overlap + overlap_duration:
                return max(start_overlap + offset_polling, time_start)

    return None


def get_next_uptime(time_start: float, num_node: int, nodes_schedule: List, duration: float = 60):
    schedule_node = nodes_schedule[num_node]

    uptime_num = 0
    for uptime, _ in schedule_node:
        if uptime == -1:
            uptime_num += 1
            continue

        if time_start <= uptime + duration:
            return max(uptime, time_start), uptime_num
        uptime_num += 1


class DependencyComputeModel:
    def __init__(self, type_dep, node_id, connected_dep, previous_use_deps: List, lp_list: List[List[float]], nodes_schedules: List = None):
        self.type_dep = type_dep
        self.node_id = node_id
        self.connected_dep = connected_dep
        self.previous_use_deps = previous_use_deps
        self.lp_list = lp_list
        self.nodes_schedules = nodes_schedules

    def _compute_time_lp_end(self, all_trans: List[float], next_uptime, uptime_num, duration: float = 60):
        time_until_sleep = self.nodes_schedules[self.node_id][uptime_num][0] + duration
        result = {}
        start = next_uptime
        current_time = next_uptime
        for i in range(len(all_trans)):
            if current_time >= time_until_sleep and i < len(all_trans):
                result[uptime_num] = {"start": round(start, 2), "end": round(current_time, 2)}
                uptime_num += 1
                start = self.nodes_schedules[self.node_id][uptime_num][0]
                current_time = start
                time_until_sleep = current_time + duration
            current_time += all_trans[i]

        result[uptime_num] = {"start": round(start, 2), "end": round(current_time, 2)}
        return current_time, result

    def compute_time(self, version_concerto_d, type_synchro):
        """
        Returns:
        The time where information is provided in case of use. The maximum end endpoints of all the actions durations
        List of all actions in time (beginning and end of each)
        """
        if len(self.previous_use_deps) > 0:
            last_previous_deps = self.previous_use_deps[-1]
            last_previous_deps_times = [lpd.compute_time(version_concerto_d, type_synchro)[0] for lpd in last_previous_deps]
        else:
            last_previous_deps_times = [0]

        m = 0
        all_results = []
        for i in range(len(last_previous_deps_times)):
            lp_list_dep = self.lp_list[i]
            next_uptime, next_uptime_num = get_next_uptime(last_previous_deps_times[i], self.node_id, self.nodes_schedules)
            time_lp_end, results = self._compute_time_lp_end(lp_list_dep, next_uptime, next_uptime_num)
            t = time_lp_end
            if t > m:
                m = t
            all_results.append(results)

        # max_results = max(all_results, key=lambda res: max([*res.values()], key=lambda val: val["end"])["end"])
        type_dep_to_sync = "provide" if type_synchro == "pull" else "use"
        if self.type_dep in [type_dep_to_sync, "intermediate"]:
            return round(m, 2), all_results
        else:
            time_use, _ = self.connected_dep.compute_time(version_concerto_d, type_synchro)
            total_lp_time = max(m, time_use)
            if version_concerto_d == "sync":
                next_information_time = get_next_overlap(total_lp_time, self.node_id, self.connected_dep.node_id, self.nodes_schedules, "sync")
            else:
                next_information_time, _ = get_next_uptime(total_lp_time, self.node_id, self.nodes_schedules)
            return round(next_information_time, 2), all_results
