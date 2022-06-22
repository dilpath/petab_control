from pathlib import Path
from typing import Dict, List, Sequence, Union

from more_itertools import one
import numpy as np
import pandas as pd
import petab
from petab import (
    get_condition_df,
    get_parameter_df,
)
from petab.C import (
    CONDITION_ID,
    NOMINAL_VALUE,
    PARAMETER_ID,
    TIME,

    LOWER_BOUND,
    UPPER_BOUND,
    ESTIMATE,
)
import petab_timecourse
from petab_timecourse import (
    PERIOD_DELIMITER,
    TIMECOURSE,
    TIMECOURSE_ID,
    get_timecourse_df,
)
from petab_timecourse.sbml import get_slug  # move to more appropriate location


from .constants import (
    CONTROL,
    ESTIMATE,
    TYPE_PATH,

    CONTROL_TIME,
    CONTROL_TARGET,

    CONTROL_ID,
    VALUE,
)
from .misc import (
    problem_experimental_conditions,
)


class TimeHorizonProblem(petab.Problem):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.original_measurement_df = self.measurement_df

    def set_horizon_measurements(
        self,
        filename: Union[str, Path],
    ):
        self.horizon_measurement_df = \
            petab.measurements.get_measurement_df(str(filename))

        self.measurement_df = petab.core.concat_tables(
            self.original_measurement_df,
            self.horizon_measurement_df,
        )


def get_switch_condition_id(
    switch_id: str,
) -> str:
    return f'condition_{switch_id}'


def get_switch_condition_df(
    switch_ids: Sequence[str],
    #target_values: Sequence[float],
    #condition_ids: Sequence[str],
):
    columns = np.diag(len(switch_ids))
    df = pd.DataFrame(data={
        #CONDITION_ID: condition_ids,
        CONDITION_ID: [
            get_switch_condition_id(switch_id)
            for switch_id in switch_ids
        ],
        **{
            switch_ids[index]: columns[:, index]
            for index in range(len(switch_ids))
        },
    })
    return petab.get_condition_df(df)


def get_switch_timecourse_df(
    switch_ids: Sequence[str],
) -> pd.DataFrame:
    pass


def read_control_df(
    df: Union[TYPE_PATH, pd.DataFrame],
) -> pd.DataFrame:
    """Read PEtab controls into a `pandas.Dataframe`.

    Arguments:
        df:
            Name of file to read from or a `pandas.Dataframe`.

    Returns:
        The control dataframe.
    """
    if not isinstance(df, pd.DataFrame):
        df = pd.read_csv(df, sep='\t', float_precision='round_trip')
    petab.lint.assert_no_leading_trailing_whitespace(
        df.columns.values,
        CONTROL,
    )
    #df.set_index([CONTROL_ID], inplace=True)
    df[VALUE] = df[VALUE].apply(petab.to_float_if_float)

    df[TIME] = df[TIME].str.split(PERIOD_DELIMITER)
    df = df.explode(TIME)
    df[TIME] = df[TIME].astype(float)

    return df


def write_control_df(df: pd.DataFrame, filename: str) -> None:
    """Write PEtab controls table.

    Arguments:
        df:
            PEtab controls table.
        filename:
            Destination file name.
    """
    with open(filename, 'w') as f:
        df.to_csv(f, sep='\t', index=False)


def parameter_controls_to_formulae(
    # FIXME reorganize code to remove circular dependencies
    # TODO make a class for sets of parameter controls, grouped by parameter ID
    parameter_controls: Dict[str, Sequence['ParameterControl']],
) -> Dict[str, str]:
    formulae = {}
    for parameter_id, controls in parameter_controls.items():
        formula = ' + '.join([
            f'{control.get_switch_parameter_id()}*'
            f'{control.get_control_parameter_id()}'
            for control in controls
        ])
        formulae[parameter_id] = formula
    return formulae


def parameter_controls_to_parameter_df(
    parameter_controls: Dict[str, Sequence['ParameterControl']],
    control_parameter_df: pd.DataFrame,
) -> pd.DataFrame:
    rows = []
    for parameter_id, controls in parameter_controls.items():
        row_template = control_parameter_df.loc[parameter_id]
        for control in controls:
            row = {
                **{PARAMETER_ID: control.get_control_parameter_id()},
                **dict(row_template),
                **{CONTROL_TIME: control.time},
            }
            if control.value == ESTIMATE:
                row[ESTIMATE] = 1
                row[NOMINAL_VALUE] = (row[UPPER_BOUND] - row[LOWER_BOUND]) / 2
            else:
                row[ESTIMATE] = 0
                # TODO assert `control.value` is in problem bounds?
                # FIXME `NOMINAL_VALUE` is an optional column?
                row[NOMINAL_VALUE] = control.value
            rows.append(row)
    parameter_df = petab.get_parameter_df(pd.DataFrame(data=rows))
    return parameter_df

def parameter_controls_to_timecourse(
    parameter_controls: Dict[str, Sequence['ParameterControl']],
    petab_problem: petab.Problem,
    problem: 'petab_control.Problem',
) -> List[pd.DataFrame]:
    # FIXME currently only one parameter can be optimized.
    #       To resolve: write method to get parameter value at arbitrary time
    #       points, by interpolating (constant) values
    if len(parameter_controls) != 1:
        raise NotImplementedError(
            'Currently only one parameter ID have be split into an optimally '
            'controlled timecourse.'
        )
    # FIXME currently assumes only one experimental condition
    #       (asserted in `petab_control.Problem.__init__`)
    condition_id = one(problem_experimental_conditions(problem))
    condition_template = {}
    if condition_id in petab_problem.condition_df.index:
        condition_template = dict(petab_problem.condition_df.loc[condition_id])

    parameter_id = one(parameter_controls)
    controls = sorted(
        parameter_controls[parameter_id],
        key=lambda control: control.time,
    )

    # TODO alternatively construct a `petab_timecourse.Timecourse`
    timecourse_data = {
        TIMECOURSE_ID: [condition_id],
        TIMECOURSE: [
            ';'.join([
                f'{control.time}:{control.get_control_condition_id()}'
                for control in controls
            ]),
        ]
    }
    timecourse_df = get_timecourse_df(pd.DataFrame(data=timecourse_data))

    condition_data = [
        {
            CONDITION_ID: control0.get_control_condition_id(),
            **condition_template,
            **{
                control.get_switch_parameter_id(): (
                    1
                    if control.get_control_condition_id()
                       == control0.get_control_condition_id()
                    else 0
                )
                for control in controls
            }
        }
        for control0 in controls
    ]
    condition_data.append({
        CONDITION_ID: condition_id,
    })

    condition_df = get_condition_df(pd.DataFrame(data=condition_data))

    return condition_df, timecourse_df

def get_controls_at_timepoint(
    parameter_controls,  # typehint
    timepoint: float,
) -> Dict[str, str]:
    sorted_controls = {
        parameter_id: sorted(
            controls,
            key=lambda control: control.time,
        )
        for parameter_id, controls in parameter_controls.items()
    }
    controls = {control_id: None for control_id in sorted_controls}
    for control_id in controls:
        for control_index, control in enumerate(sorted_controls[control_id]):
            if (
                # Current control is at or before the timepoint
                control.time <= timepoint
                and (
                    # Next control is after the timepoint
                    (
                        control_index + 1 < len(sorted_controls[control_id])
                        and sorted_controls[control_id][control_index + 1].time > timepoint
                    )
                    # Or this is the last control
                    or (
                        control_index + 1 == len(sorted_controls[control_id])
                    )
                )
            ):
                controls[control_id] = control
                break
    return controls

def parameter_controls_to_timecourse_new(
    parameter_controls: Dict[str, Sequence['ParameterControl']],
    petab_problem: petab.Problem,
    problem: 'petab_control.Problem',
) -> List[pd.DataFrame]:
    # FIXME currently assumes only one experimental condition
    #       (asserted in `petab_control.Problem.__init__`)
    condition_id = one(problem_experimental_conditions(problem))
    condition_template = {}
    if condition_id in petab_problem.condition_df.index:
        condition_template = dict(petab_problem.condition_df.loc[condition_id])

    times = sorted(set(
        control.time
        for controls in parameter_controls.values()
        for control in controls
    ))

    timecourse_condition_ids = {
        time: f'timecourse_condition_{get_slug(time)}'
        for time in times
    }

    timecourse_data = {
        TIMECOURSE_ID: [condition_id],
        TIMECOURSE: [
            ';'.join([
                f'{time}:{timecourse_condition_id}'
                for time, timecourse_condition_id in timecourse_condition_ids.items()
            ]),
        ]
    }
    timecourse_df = get_timecourse_df(pd.DataFrame(data=timecourse_data))

    condition_data = [
        {
            CONDITION_ID: timecourse_condition_id,
            **condition_template,

            **{
                parameter_id: (
                    control.get_control_parameter_id()
                    if control is not None
                    else None
                )
                for parameter_id, control in get_controls_at_timepoint(
                    parameter_controls,
                    time,
                ).items()
            }
        }
        for time, timecourse_condition_id in timecourse_condition_ids.items()
    ]
    condition_data.append({
        CONDITION_ID: condition_id,
    })

    condition_df = get_condition_df(pd.DataFrame(data=condition_data))

    parameter_data = [
        {
            PARAMETER_ID: control.get_control_parameter_id(),
            **problem.control_parameter_df.loc[parameter_id].to_dict(),
            ESTIMATE: 1,
            CONTROL_TARGET: control.target_id,
            CONTROL_TIME: control.time,
        }
        for parameter_id, controls in parameter_controls.items()
        for control in controls
    ]

    parameter_df = get_parameter_df(pd.DataFrame(data=parameter_data))

    return condition_df, parameter_df, timecourse_df
