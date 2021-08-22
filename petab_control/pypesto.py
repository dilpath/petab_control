from typing import Dict, Tuple

from .misc import unscale_parameters

def get_parameters_from_pypesto_result(
    pypesto_result,
    pypesto_problem,
    petab_problem,
) -> Tuple[Dict[str, float], Dict[str, float]]:
    scaled_parameters = dict(zip(
        pypesto_problem.x_names,
        pypesto_result.optimize_result.list[0]['x'],
    ))
    unscaled_parameters = \
        unscale_parameters(scaled_parameters, petab_problem)
    return scaled_parameters, unscaled_parameters

