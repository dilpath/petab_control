from typing import Dict, Tuple


def get_parameters_from_pypesto_result(
    pypesto_result,
    pypesto_problem,
    petab_problem,
) -> Tuple[Dict[str, float], Dict[str, float]]:
    scaled_parameters = dict(zip(
        pypesto_problem.x_names,
        pypesto_result.optimize_result.list[0]['x'],
    ))
    unscaled_parameters = petab_problem.unscale_parameters(scaled_parameters)
    return scaled_parameters, unscaled_parameters
