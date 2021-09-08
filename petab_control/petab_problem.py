from pathlib import Path
from typing import Dict, List, Sequence, Union

from more_itertools import one
import numpy as np
import pandas as pd
import petab
from petab import (
    get_condition_df,
)
from petab.C import (
    CONDITION_ID,
    NOMINAL_VALUE,
    PARAMETER_ID,
    TIME,

    LOWER_BOUND,
    UPPER_BOUND,
)
import petab_timecourse
from petab_timecourse import (
    TIMECOURSE,
    TIMECOURSE_ID,
    get_timecourse_df,
)


from .constants import (
    CONTROL,
    ESTIMATE,
    PATH_LIKE,
    TYPE_PATH,

    CONTROL_TIME,

    CATEGORY,
    ORIGINAL,
)
#from .control import (
#    get_control_condition_id,
#    get_control_parameter_id,
#    get_switch_parameter_id,
#)
from .misc import (
    problem_experimental_conditions,
)
from .problem import Problem


def control_problem_to_petab_problem(
    control_problem: Problem,
) -> petab.Problem:
    """Create a PEtab problem from a PEtab control problem.

    Args:
        control_problem:
            A PEtab Control problem object instance.

    Returns:
        A PEtab problem, which can be optimized by any PEtab-compatible
        calibration tool to solve the optimal control problem.
    """
    petab_problem = control_problem.get_control_petab_problem()
    petab_timecourse.sbml.add_timecourse_as_events(
        petab_problem,
        timecourse_id=one(petab_problem.timecourse_df.index),
    )
    return petab_problem


def control_problem_yaml_to_petab_problem(
    control_problem_yaml: TYPE_PATH,
    # FIXME include path to `petab_problem0` PEtab problem YAML file
    # in the PEtab Control YAML file?
    # Would then need a helper method to easily customize in the case of
    # ensemble problems.
    petab_problem0: Union[petab.Problem, TYPE_PATH],
) -> petab.Problem:
    """Create a PEtab problem from a PEtab Control YAML file.

    Args:
        control_problem_yaml:
            The location of the PEtab Control YAML file.
        petab_problem0:
            The PEtab problem to be used as a based for the PEtab Control
            problem. This includes the model.

    Returns:
        A PEtab problem, which can be optimized by any PEtab-compatible
        calibration tool to solve the optimal control problem.
    """
    #if isinstance(petab_problem0, TYPE_PATH):
    if not isinstance(petab_problem0, petab.Problem):
        petab_problem0 = petab.Problem.from_yaml(str(petab_problem0))

    control_problem = Problem.from_yaml(
        yaml_path=str(control_problem_yaml),
        petab_problem=petab_problem0,
    )
    return control_problem_to_petab_problem(control_problem)


def get_combined_petab_problem(
    control_yaml,
    petab_yaml,
) -> petab.Problem:
    original_petab_problem = petab.Problem.from_yaml(str(petab_yaml))
    #original_petab_problem = get_original_petab_problem()
    control_petab_problem = \
        control_problem_yaml_to_petab_problem(
            control_yaml,
            petab_yaml,
            #petab.Problem.from_yaml(str(petab_output_path / 'problem.yaml')),
        )
    #control_petab_problem = get_original_control_petab_problem()
    original_petab_problem.measurement_df[CATEGORY] = ORIGINAL
    control_petab_problem.measurement_df[CATEGORY] = CONTROL
    original_petab_problem.parameter_df[CATEGORY] = ORIGINAL
    control_petab_problem.parameter_df[CATEGORY] = CONTROL
    #combined_petab_problem = get_original_control_petab_problem()

    combined_petab_problem = \
        control_problem_yaml_to_petab_problem(
            control_yaml,
            petab_yaml,
            #petab.Problem.from_yaml(str(petab_output_path / 'problem.yaml')),
        )
    combined_petab_problem.measurement_df = pd.concat([
        original_petab_problem.measurement_df,
        control_petab_problem.measurement_df,
    ])
    combined_petab_problem.parameter_df = pd.concat([
        original_petab_problem.parameter_df,
        control_petab_problem.parameter_df,
    ])
    return combined_petab_problem


def get_finite_petab_problem(
    petab_problem: petab.Problem,
    t0: float,
    t1: float,
    #current_time,
    #original_petab_problem=original_petab_problem,
    #past_horizon=past_horizon,
    #future_horizon=future_horizon,
    #update_period=update_period,
    nominal_values: Dict[str, float] = None,
    inclusive='left',
) -> petab.Problem:
    """Truncate a combined PEtab problem.

    Args:
        petab_problem:
            A combined PEtab problem (e.g. the returned value from the
            `petab_control.petab.get_combined_petab_problem` method).
        t0:
            The start of the time window.
        t1:
            The end of the time window.
        nominal_values:
            Update the PEtab problem parameter table nominal values with
            a dictionary where keys are parameter IDs and values are
            nominal values (e.g. fix parameters to a previous estimate, for
            optimization of a subsequent fitting or optimal control).
        inclusive:
            How the bounds `t0` and `t1` are treated (passed on to the
            `pandas.Series.between` method).

    Returns:
        The truncated PEtab problem.
    """
    #petab_problem = get_full_combined_petab_problem()

    # Fix control parameters to zero.
    petab_problem.parameter_df[ESTIMATE].loc[
        petab_problem.parameter_df[CATEGORY] == CONTROL
    ] = 0
    petab_problem.parameter_df[NOMINAL_VALUE].loc[
        petab_problem.parameter_df[CATEGORY] == CONTROL
    ] = 0
    # Fix previously estimated control parameters
    if nominal_values is not None:
        nominal_values_series = pd.Series(nominal_values, name=NOMINAL_VALUE)
        petab_problem.parameter_df.update(nominal_values_series)

    petab_problem.measurement_df = petab_problem.measurement_df.loc[
        petab_problem.measurement_df[TIME].between(
            t0,
            t1,
            inclusive=inclusive,
        )
    ]
    petab_problem.measurement_df.drop(
        petab_problem.measurement_df.index[
            petab_problem.measurement_df[CATEGORY] == CONTROL,
        ],
        inplace=True,
    )
    return petab_problem


def get_finite_control_petab_problem(
    petab_problem: petab.Problem,
    t0: float,
    t1: float,
    #current_time,
    #original_petab_problem=original_petab_problem,
    #past_horizon=past_horizon,
    #future_horizon=future_horizon,
    #update_period=update_period,
    nominal_values: Dict[str, float] = None,
    inclusive: str = 'left',
) -> petab.Problem:
    """Truncate a combined PEtab problem.

    Args:
        petab_problem:
            A combined PEtab problem (e.g. the returned value from the
            `petab_control.petab.get_combined_petab_problem` method).
        t0:
            The start of the time window.
        t1:
            The end of the time window.
        nominal_values:
            Update the PEtab problem parameter table nominal values with
            a dictionary where keys are parameter IDs and values are
            nominal values (e.g. fix parameters to a previous estimate, for
            optimization of a subsequent fitting or optimal control).
        inclusive:
            How the bounds `t0` and `t1` are treated (passed on to the
            `pandas.Series.between` method).

    Returns:
        The truncated PEtab problem.
    """

    # Only estimate control parameters
    petab_problem.parameter_df[ESTIMATE].loc[
        petab_problem.parameter_df[CATEGORY] == ORIGINAL
    ] = 0
    #petab_problem.parameter_df[NOMINAL_VALUE].loc[
    #    petab_problem.parameter_df[CATEGORY] == ORIGINAL
    #] = 0

    # Only estimate control parameters for current future time window
    desired_control_times = petab_problem.parameter_df[CONTROL_TIME].between(
        t0,
        t1,
        inclusive=inclusive,
    )
    petab_problem.parameter_df[ESTIMATE].loc[~desired_control_times] = 0
    # Just in case, can prevent earlier "skipped" (never estimated in a finite
    # horizon loop iteration) controls from being fixed to
    # their value in the PEtab parameter table.
    petab_problem.parameter_df[NOMINAL_VALUE].loc[~desired_control_times] = 0

    later_control_times = petab_problem.parameter_df[CONTROL_TIME].between(
        t1,
        np.inf,
        inclusive=inclusive,
    )
    latest_control_df = petab_problem.parameter_df.loc[desired_control_times]
    latest_control_value = latest_control_df.loc[latest_control_df.control_time==latest_control_df.control_time.max()]
    latest_control_id = nominal_values[one(latest_control_value.index)]
    #breakpoint()
    petab_problem.parameter_df[NOMINAL_VALUE].loc[~desired_control_times] = 0

    # Should never be `None` unless optimal control is performed before fitting
    # for some reason.
    if nominal_values is not None:
        nominal_values_series = pd.Series(nominal_values, name=NOMINAL_VALUE)
        petab_problem.parameter_df.update(nominal_values_series)

    # subset measurements
    petab_problem.measurement_df = petab_problem.measurement_df.loc[
        petab_problem.measurement_df[TIME].between(
            t0,
            t1,
            inclusive=inclusive,
        )
    ]
    petab_problem.measurement_df.drop(
        petab_problem.measurement_df.index[
            petab_problem.measurement_df[CATEGORY] == ORIGINAL,
        ],
        inplace=True,
    )
    return petab_problem
