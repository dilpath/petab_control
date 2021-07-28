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
    #test_condition = problem.control_df[SIMULATION_CONDITION_ID][0]
    #print(test_condition)
    #for df in [problem.control_df, problem.objective_observable_df]:
    #    if not (df[SIMULATION_CONDITION_ID] == test_condition).all():
    #        return False
    #return True


def unscale_parameters(
    scaled_parameters: Dict[str, float],
    petab_problem: petab.Problem,
):
    scales = dict(petab_problem.parameter_df[PARAMETER_SCALE])

    unscaled_parameters = {
        parameter_id: petab.parameters.unscale(
            parameter_value,
            scales[parameter_id],
        )
        for parameter_id, parameter_value in scaled_parameters.items()
    }

    return unscaled_parameters


def add_estimate(
    estimate: Dict[str, float],
    estimate_petab_problem: petab.Problem,
    control_petab_problem: petab.Problem
) -> petab.Problem:
    """Add a parameter estimate as fixed values to a PEtab problem.

    This is a convenience method to facilitate the transition from parameter
    estimation with a PEtab problem and real measurements, to an optimal
    control PEtab problem that should use the fitting result.

    Arguments:
        estimate:
            The parameter estimates, where keys are parameter IDs that exist
            in the index of the estimate PEtab parameter table. Note that the
            values should be unscaled. See the `unscale_parameters` method for
            a convenience method to do this.
        estimate_petab_problem:
            The PEtab problem used to generate the parameter estimates.
        control_petab_problem:
            The PEtab problem for optimal control.
    """
    parameter_df = estimate_petab_problem.parameter_df.copy(deep=True)
    # Keep only estimated parameters. Presumably, estimated parameters are not
    # in the control PEtab parameters table, so can be added as fixed nominal
    # parameters. However, the same fixed parameter may exist in both the
    # optimize and control PEtab parameter table, hence should be left to the
    # user and not automatically duplicated.
    # FIXME check for conflicts e.g. parameter already exists in control
    # PEtab parameter table.
    parameter_df = parameter_df.loc[estimate]
    parameter_df[NOMINAL_VALUE].update(estimate)
    parameter_df[ESTIMATE] = 0

    control_petab_problem.parameter_df = \
        pd.concat([control_petab_problem.parameter_df, parameter_df])


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
    unscaled_parameters = \
        unscale_parameters(scaled_parameters, estimate_petab_problem)
    add_estimate(
        unscaled_parameters,
        estimate_petab_problem,
        control_petab_problem,
    )
