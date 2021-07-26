from pathlib import Path
from typing import List, Set

from petab.C import (
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
