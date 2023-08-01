import jinja2
import simulation_functions

templateLoader = jinja2.FileSystemLoader(searchpath="./concerto-d")
templateEnv = jinja2.Environment(loader=templateLoader)
TEMPLATE_FILE = "platform.yaml.j2"
template = templateEnv.get_template(TEMPLATE_FILE)

sweeper = simulation_functions.get_simulation_swepped_parameters()

for parameter in sweeper:
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
    outputText = template.render(
        stressConso=stressConso,
        idleConso=idleConso,
        bandwidth=bandwidth,
        commsConso=commsConso,
        typeSynchro=typeSynchro
    )

    joined_params = simulation_functions.get_params_joined(parameter)
    with open(f"concerto-d/platform-{joined_params}.yaml", "w") as f:
        f.write(outputText)
