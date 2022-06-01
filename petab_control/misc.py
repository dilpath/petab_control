from pathlib import Path
from typing import Dict, Set

import pandas as pd
import petab
from petab.C import (
    ESTIMATE,
    NOMINAL_VALUE,
    PARAMETER_SCALE,
    SIMULATION_CONDITION_ID,
)

from .constants import (
    PATH_LIKE,
)


def parse_path(path: PATH_LIKE) -> Path:
    return Path(path)


def problem_experimental_conditions(
    problem: 'petab_control.Problem',
) -> Set[str]:
    """Get the experimental condition IDs of a problem.

    Arguments:
        problem:
            The PEtab control problem.

    Returns:
        The set of experimental condition IDs.
    """
    conditions = set(
        list(problem.control_df[SIMULATION_CONDITION_ID]) +
        list(problem.objective_measurement_df[SIMULATION_CONDITION_ID])
    )
    return conditions


def add_estimate(
    estimate: Dict[str, float],
    estimate_petab_problem: petab.Problem,
    control_petab_problem: petab.Problem,
    unscale: bool = False,
) -> petab.Problem:
    """Add a parameter estimate as fixed values to a PEtab problem.

    This is a convenience method to facilitate the transition from parameter
    estimation with a PEtab problem and real measurements, to an optimal
    control PEtab problem that should use the fitting result.

    Arguments:
        estimate:
            The parameter estimates, where keys are parameter IDs that exist
            in the index of the estimate PEtab parameter table. Note that the
            values should be unscaled (e.g. use `unscale=True`).
        estimate_petab_problem:
            The PEtab problem used to generate the parameter estimates.
        control_petab_problem:
            The PEtab problem for optimal control.
        unscale:
            Whether to unscale the parameters.
    """
    if unscale:
        estimate = estimate_petab_problem.unscale_parameters(estimate)

    parameter_df = estimate_petab_problem.parameter_df.copy(deep=True)

    parameter_df[ESTIMATE].update({
        parameter_id: 0
        for parameter_id in estimate
    })

    parameter_df[NOMINAL_VALUE].update({
        parameter_id: value
        for parameter_id, value in estimate.items()
    })

    control_petab_problem.parameter_df = parameter_df


def add_estimate_from_pypesto_result(
    pypesto_result: 'pypesto.Result',
    estimate_petab_problem: petab.Problem,
    control_petab_problem: petab.Problem,
):
    """Add a pyPESTO parameter estimate as fixed values to a PEtab problem.

    Arguments:
        pypesto_result:
            A pyPESTO result that includes the result of an optimization.
        estimate_petab_problem:
            See the `add_estimate` method.
        control_petab_problem:
            See the `add_estimate` method.
    """
    scaled_parameters = dict(zip(
        pypesto_result.problem.x_names,
        pypesto_result.optimize_result.list[0]['x'],
    ))
    add_estimate(
        estimate=scaled_parameters,
        estimate_petab_problem=estimate_petab_problem,
        control_petab_problem=control_petab_problem,
        unscale=True,
    )
