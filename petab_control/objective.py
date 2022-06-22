from functools import partial
from itertools import chain
from typing import Any, Dict, List, Sequence, Tuple, Union
import warnings

import amici
from amici.petab_import import import_petab_problem
from amici.petab_objective import (
    RDATAS
)
from more_itertools import one
import petab
from petab.C import (
    CONDITION_NAME,
    ESTIMATE,
    PARAMETER_ID,
)

import pypesto.objective
import pypesto.petab

from petab_timecourse import Timecourse
from petab_timecourse import Simulator


from .constants import (
    PERIODS,
    PERIODS_RESULTS,
)
from .problem import Problem

from amici.petab_objective import (
    LLH,
    SLLH,
)


from pypesto.C import (
    FVAL,
    GRAD,
    MODE_FUN,
)

from pypesto.objective import Objective


# pyPESTO expects an objective function to provide
# its output in the following order.
PYPESTO_FUNCTION_ORDER = [
    FVAL,
    GRAD,
]


def pypesto_fun(
    x: Sequence[float],
    petab_control_problem: Problem,
    x_names: Sequence[str],
):
    """Get pyPESTO-compatible objective information.

    Args:
        x:
            The parameter vector from pyPESTO.
        petab_control_problem:
            The PEtab Control problem. NB: should already be
            setup with a simulator.
        x_names:
            The parameter IDs, with an order that corresponds to
            `x`.

    Returns:
        The objective result.
    """
    problem_parameters = dict(zip(x_names, x))

    results = petab_control_problem.simulate(
        problem_parameters=problem_parameters,
    )

    estimated_parameters = (
        petab_control_problem
        .control_parameter_df
        .loc[
            petab_control_problem
            .control_parameter_df
            [ESTIMATE]
            ==
            1
        ]
        .index
    )

    grad = {
        id_: 0
        for id_ in
        [
            *petab_control_problem.simulator_control_parameters,
            *problem_parameters,
        ]
    }
    for period_index in range(len(
        petab_control_problem
        .simulator
        .timecourse
        .periods
    )):
        gradients_assigned = {
            parameter_id: False
            for parameter_id in estimated_parameters
        }
        for control_parameter_id, control_information in (
            petab_control_problem
            .simulator_control_parameters
            .items()
        ):
            if period_index not in control_information[PERIODS]:
                continue

            parameter_id = control_information[PARAMETER_ID]

            grad[control_parameter_id] += (
                results
                [PERIODS_RESULTS]
                [period_index]
                [SLLH]
                [control_information[PARAMETER_ID]]
            )

            if parameter_id in gradients_assigned:
                gradients_assigned[parameter_id] = True
            gradients_assigned[control_information[PARAMETER_ID]] = True

        # FIXME parameters that have corresponding control
        #       parameters
        for parameter_id in problem_parameters:
            if (
                parameter_id not in gradients_assigned
                or gradients_assigned[parameter_id]
            ):
                #if gradients_assigned.get(parameter_id, True):
                continue
            grad[parameter_id] += (
                results
                [PERIODS_RESULTS]
                [period_index]
                [SLLH]
                [parameter_id]
            )

    result_dict = {
        FVAL: -results[LLH],
        GRAD: [
            -grad[parameter_id]
            for parameter_id in x_names
        ]
    }

    result = [
        result_dict[output]
        for output in PYPESTO_FUNCTION_ORDER
    ]

    return result


def get_pypesto_problem(
    petab_control_problem: Problem,
    setup_simulator_kwargs: Dict,
    petab_importer_kwargs: Dict,
):
    petab_control_problem.setup_simulator(**setup_simulator_kwargs)

    x_names = [
        x_name
        for x_index, x_name in enumerate(
            petab_control_problem
            .optimizer_control_petab_problem
            .parameter_df
            .index
        )
    ]

    pypesto_importer = pypesto.petab.PetabImporter(
        petab_problem=(
            petab_control_problem
            .optimizer_control_petab_problem
        ),
        **petab_importer_kwargs,
    )

    pypesto_problem = pypesto_importer.create_problem(
        objective=pypesto.objective.Objective(
            fun=partial(
                pypesto_fun,
                petab_control_problem=petab_control_problem,
                x_names=x_names,
            ),
            grad=True,
        ),
        problem_kwargs={'copy_objective': False},
    )

    return pypesto_problem
