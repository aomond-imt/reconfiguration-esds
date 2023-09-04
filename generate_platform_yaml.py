import jinja2
import simulation_functions

templateLoader = jinja2.FileSystemLoader(searchpath="./concerto_d_esds_simulation")
templateEnv = jinja2.Environment(loader=templateLoader)
TEMPLATE_FILE = "platform.yaml.j2"
template = templateEnv.get_template(TEMPLATE_FILE)
nb_deps = 30

sweeps = simulation_functions.get_simulation_swepped_parameters()
nodes_per_batch = nb_deps+2
nodes_count = nodes_per_batch * 4

for parameter in sweeps:
    (
        stressConso,
        idleConso,
        nameTechno,
        bandwidth,
        commsConso,
        typeSynchro
    ) = (
        parameter["stressConso"],
        parameter["idleConso"],
        parameter["techno"]["name"],
        parameter["techno"]["bandwidth"],
        parameter["techno"]["commsConso"],
        parameter["typeSynchro"]
    )
    communicating_nodes = ", ".join(str(node_num) for node_num in range(nodes_per_batch*2, nodes_per_batch*4))
    links_eth0 = []
    for sending_num in range(nodes_per_batch*2, nodes_per_batch*3-1):
        nodes_receives = ','.join(str(receive_num) for receive_num in range(nodes_per_batch*3, nodes_per_batch*4-1) if (receive_num-nodes_per_batch) != sending_num)
        links_eth0.append(
            f"- {sending_num} {bandwidth} 0s {nodes_receives}"
        )
        links_eth0.append(
            f"- {nodes_receives} {bandwidth} 0s {sending_num}"
        )
    # TODO: ad-hoc routeur links
    links_eth0Router = []
    for sending_num in range(nodes_per_batch*2, nodes_per_batch*3):
        nodes_receives = ','.join(str(receive_num) for receive_num in range(nodes_per_batch*3, nodes_per_batch*4) if (receive_num-nodes_per_batch) != sending_num)
        links_eth0Router.append(
            f"- {sending_num} {bandwidth} 0s {nodes_receives}"
        )
        links_eth0Router.append(
            f"- {nodes_receives} {bandwidth} 0s {sending_num}"
        )
    outputText = template.render(
        nodes_count=nodes_count,
        nodes_per_batch=nodes_per_batch,
        communicating_nodes=communicating_nodes,
        stressConso=stressConso,
        idleConso=idleConso,
        bandwidth=bandwidth,
        nameTechno=nameTechno,
        commsConso=commsConso,
        typeSynchro=typeSynchro,
        links_eth0=links_eth0,
        links_eth0Router=links_eth0Router
    )

    joined_params = simulation_functions.get_params_joined(parameter)
    with open(f"concerto_d_esds_simulation/platform-{joined_params}.yaml", "w") as f:
        f.write(outputText)
