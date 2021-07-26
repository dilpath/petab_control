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
from petab_timecourse import (
    TIMECOURSE,
    TIMECOURSE_ID,
    get_timecourse_df,
)


from .constants import (
    CONTROL,
    ESTIMATE,
    PATH_LIKE,
)
#from .control import (
#    get_control_condition_id,
#    get_control_parameter_id,
#    get_switch_parameter_id,
#)
from .misc import (
    problem_experimental_conditions,
)
#from .problem import Problem


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
#def generate_problem_petab(
#    problem: Problem,
#    petab_problem: petab.Problem,
#    #sbml_filename: str,
#    output_path: Union[str, Path],
#) -> None:
#

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
    df: Union[PATH_LIKE, pd.DataFrame],
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
                **dict(row_template)
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
#) -> Dict[str, pd.DataFrame]:
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

    #control_times = []
    #control_ordered = []
    #controls = 
    #parameter_controls = problem.
    parameter_id = one(parameter_controls)
    controls = sorted(
        parameter_controls[parameter_id],
        key=lambda control: control.time,
    )
    #for parameter_id, controls in parameter_controls.items():
    #    for control in controls:
    #        control_times.append(control.time)
    #        control_ordered.append(control.get_control_condition_id())

    # TODO alternatively construct a `petab_timecourse.Timecourse`
    timecourse_data = {
        TIMECOURSE_ID: [condition_id],
        TIMECOURSE: [
            ';'.join([
                #f'{control[TIME]}:{get_control_condition_id(control)}'
                f'{control.time}:{control.get_control_condition_id()}'
                for control in controls
                #for time, control_condition_id
                #in zip(control_times, control_condition_ids)
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
        #for control_condition_id0 in control_condition_ids
        for control0 in controls
    ]
    condition_data.append({
        CONDITION_ID: condition_id,
    })

    condition_df = get_condition_df(pd.DataFrame(data=condition_data))

    return condition_df, timecourse_df
    #return {
    #    'condition_df': condition_df,
    #    'timecourse_df': timecourse_df,
    #}
