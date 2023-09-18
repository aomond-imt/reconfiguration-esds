import copy
import json
import sys

nb_rounds_ups = 45
uptime_duration = 60
nb_nodes = 31


def compute_covering_time_dep(dep_num: int, round: int, time_awoken: float, all_dep_uptimes):
    uptimes_dep = all_dep_uptimes[dep_num]
    all_other_uptimes = [all_dep_uptimes[i] for i in range(len(all_dep_uptimes)) if dep_num != i]
    overlaps_list = []
    for other_uptimes_dep in all_other_uptimes:
        covering_time = 0
        for uptime_dep in uptimes_dep:
            for other_uptime_dep in other_uptimes_dep:
                if other_uptime_dep == [-1, -1] or uptime_dep == [-1, -1]:
                    overlap = 0
                else:
                    overlap = min(uptime_dep[0] + time_awoken, other_uptime_dep[0] + time_awoken) - max(uptime_dep[0], other_uptime_dep[0])
                covering_time += overlap if overlap > 0 else 0

        percentage_overlap = covering_time/(time_awoken*round)
        overlaps_list.append(percentage_overlap)

    return overlaps_list


def compute_overlap_for_round(round_num, output, nb_appearances, combo=None, combo_up=None):
    if combo == None:
        combo = []
    if combo_up == None:
        combo_up = []
    r = f"--- FREQ: {round_num} -----\n"
    uptimes_str_list = []
    server_dep_str_list = []
    overlap_values_list = []
    typeOverlap_list = []
    for k in range(1, nb_nodes):
        o0, s0 = output[0][round_num]
        o2, s2 = output[k][round_num]
        uptime_server = f"[{o0}, {uptime_duration}]"
        uptime_dep = f"[{round(o2, 3)}, {uptime_duration}]"
        uptime_str = uptime_server + uptime_dep
        if o0 == -1 or o2 == -1:
            overlap_value = 0
        else:
            overlap_value = round(max(min(o0 + uptime_duration, o2 + uptime_duration) - max(o0, o2), 0), 3)
        if o0 == -1 or o2 == -1:
            typeOverlap = "None"
        elif o2 < o0:
            typeOverlap = "Left"
        elif o2 > o0:
            typeOverlap = "Right"
        else:
            typeOverlap = "Full"
        uptimes_str_list.append(uptime_str)
        server_dep_str_list.append(f"Server/dep{k - 1}")
        overlap_values_list.append(str(overlap_value))
        typeOverlap_list.append(typeOverlap)
        if overlap_value > 0:
            nb_appearances[k - 1] += 1
            if k < nb_nodes and k not in combo:
                combo.append(k)
        if o2 > 0 and k not in combo_up:
            combo_up.append(k)

    max_len_uptimes_str_list = len(max(uptimes_str_list, key=lambda element: len(element)))
    max_len_server_dep_str_list = len(max(server_dep_str_list, key=lambda element: len(element)))
    max_list_overlap_values_list = len(max(overlap_values_list, key=lambda element: len(element)))
    offset = 3
    for k in range(0, len(uptimes_str_list)):
        result_str = uptimes_str_list[k].ljust(max_len_uptimes_str_list + offset, ' ')
        result_str += server_dep_str_list[k].ljust(max_len_server_dep_str_list + offset, ' ')
        result_str += overlap_values_list[k].ljust(max_list_overlap_values_list + offset, ' ')
        result_str += typeOverlap_list[k]
        r += f"{result_str}\n"
    r += "-----------------\n\n"
    return r, nb_appearances, combo, combo_up


if __name__ == "__main__":
    # default_file_name = "uptimes-60-30-12-0_02-0_05"
    # default_file_name = "uptimes-60-30-12-0_2-0_3"
    # default_file_name = "uptimes-60-30-12-0_5-0_6"
    # default_file_name = "uptimes-60-30-12-0_7-0_8"
    # default_file_name = "uptimes-60-30-12-0_8-0_9"
    # default_file_name = "uptimes-60-30-12-0_5-0_6-generated"
    # default_file_name = "uptimes-60-50-12-0_02-0_02-generated"
    # default_file_name = "uptimes-30-50-12-0_02-0_02-generated-best"
    # default_file_name = "uptimes-36-50-12-0_02-0_02-generated"
    # default_file_name = "mascots_uptimes-60-50-5-ud0_od0_7_25_perc-dao"
    # default_file_name = "uptimes-36-50-12-0_25-0_25-generated-again"
    # default_file_name = "uptimes-36-50-12-0_25-0_25"
    # default_file_name = "uptimes-36-50-12-0_5-0_5-generated-again"
    # default_file_name = "uptimes-36-50-12-1-1"
    default_file_name = "uptimes-dao-60-sec"
    file_name = sys.argv[1] if len(sys.argv) > 1 else f"{default_file_name}.json"
    output = json.load(open(file_name))
    result = ""
    result += file_name + "\n"
    nb_appearances = [0] * (nb_nodes-1)
    # file_output = open(f"output_overlaps_{default_file_name}.txt", "w")
    file_output = sys.stdout
    combo = []
    count_combo = []
    combo_up = []
    count_combo_up = []
    for round_num in range(len(output[0])):
        old_combo = copy.deepcopy(combo)
        r, nb_appearances, combo, combo_up = compute_overlap_for_round(round_num, output, nb_appearances, combo, combo_up)
        result += r
        if len(combo) == nb_nodes-1:
            last_added = set(combo) - set(old_combo)
            combo = [*last_added]
            count_combo += [round_num]
            # print(f"COMBO{count_combo}: round_num {round_num}", file=file_output)
        if len(combo_up) == nb_nodes-1:
            combo_up = []
            count_combo_up += [round_num]
            # print(f"COMBO_UP{count_combo_up}: round_num {round_num}", file=file_output)
    print(result, file=file_output)
    print("---- COMBO SYNC ----")
    print(count_combo)
    print("---- COMBO ASYNC ----")
    print(count_combo_up)

    # for i, c in enumerate(count_combo):
    #     print(f"COMBO{i}: {c}", file=file_output)
    # for i, c in enumerate(count_combo_up):
    #     print(f"COMBO_UP{i}: {c}", file=file_output)

    dep_num = 0  # Check only server
    # cov_perc_list = compute_covering_time_dep(dep_num, nb_rounds_ups, uptime_duration, output)
    # server_means_coverage = round(sum(cov_perc_list) / len(cov_perc_list), 2)

    # print(f"Total mean coverage: {server_means_coverage}", file=file_output)

    # Nb appearance
    print(f"Appearances: {nb_appearances}", file=file_output)

