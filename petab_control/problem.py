import abc
import copy
from dataclasses import dataclass
from typing import Any, Dict, List, Sequence, Union
import warnings

import libsbml
from more_itertools import one
import numpy as np
import pandas as pd
import petab
#from amici.petab_objective import (
#    LLH,
#    SLLH,
#)
from petab import (
    get_measurement_df,
    get_observable_df,
    get_parameter_df,
)
from petab.C import (
    CONDITION_ID,
    NOMINAL_VALUE,
    PARAMETER_ID,
    SIMULATION_CONDITION_ID,
    TIME,
    TIME_STEADY_STATE,
)
# FIXME rename to `slugify` convention?
import petab_timecourse
from petab_timecourse.sbml import get_slug as slugify
from petab_timecourse import Timecourse, Period
from petab_timecourse.C import (
    PERIOD_DELIMITER,
    TIME_CONDITION_DELIMITER,
    TIMECOURSE,
    TIMECOURSE_ID,
    PERIOD,
)
#from petab_timecourse.simulator import (
#    Simulator,
#    #AmiciSimulator,
#)
import yaml

from .constants import (
    #DEFAULT_VALUE,
    DUMMY_VALUE,
    ZERO,
    ESTIMATE,
    PARAMETER,
    STATE,

    TYPE_PATH,

    PROBLEMS,
    CONTROL,
    CONTROL_TARGET,
    CONTROL_TIME,
    PROBLEM_ID,
    START_TIME,
    CONTROL_FILES,
    OBJECTIVE,
    CONTROL_PARAMETER_FILES,
    MEASUREMENT_FILES,
    OBSERVABLE_FILES,
    PERIODS,

    CONTROL_CONDITION_ID,
    CONTROL_TIMECOURSE_ID,
    LAST_MEASURED_TIMEPOINT,
    VALUE,
    #PARAMETER_CONTROL_ID,
    CONTROL_ID,
    PERIODS_RESULTS,
)
from .misc import (
    parse_path,
    problem_experimental_conditions,
)
from .sbml import (
    add_parameter,
    add_assignment_rule,
)
from .petab import (
    get_switch_condition_df,
    parameter_controls_to_formulae,
    parameter_controls_to_parameter_df,
    parameter_controls_to_timecourse_new,
    read_control_df,
)

NUMERIC = Union[float, int]
NUMERIC_OR_STRING = Union[float, int, str]


class Target(abc.ABC):
    target_type: str = None

    def __init__(
        self,
        target_id: str,
    ):
        self.target_id = target_id


class ParameterTarget(Target):
    target_type = PARAMETER


class StateTarget(Target):
    target_type = STATE


class SpeciesTarget(StateTarget):
    pass


class Values():
    def __init__(
        self,
        values: Union[NUMERIC_OR_STRING, Sequence[NUMERIC_OR_STRING]],
    ):
        self.singular = False
        if (
            isinstance(values, str) or
            isinstance(values, float) or
            isinstance(values, int)
        ):
            self.singular = True

        self.values = values

    def __getitem__(self, i: int):
        if self.singular:
            return self.values
        else:
            return self.values[i]


class Timepoints():
    def __init__(
        self,
        start: NUMERIC_OR_STRING,
        timepoints: Sequence[NUMERIC_OR_STRING],
    ):
        self.timepoints = timepoints

    def __getitem__(self, i: int):
        return self.timepoints[i]

    def __len__(self):
        return len(self.timepoints)


class Control():
    def __init__(
        self,
        target_id: str,
        # change to `petab_timecourse.Period` object?
        time: NUMERIC_OR_STRING,
        value: NUMERIC_OR_STRING,
    ):
        self.target_id = target_id
        self.time = time
        self.value = value

    def get_id(self) -> str:
        return (
            f'target__{self.target_id}' + '__'
            f'time__{slugify(self.time)}' + '__'
            f'value__{slugify(self.value)}'
        )


class ParameterControl(Control):
    def __init__(
        self,
        parameter_id: str,
        *args,
        **kwargs,
    ):
        super().__init__(
            target_id=parameter_id,
            *args,
            **kwargs
        )

    def get_control_parameter_id(self):
        return f'control_parameter__{self.get_id()}'

    def get_switch_parameter_id(self):
        return f'switch_parameter__{self.get_id()}'

    def get_control_condition_id(self):
        return f'control_condition__{self.get_id()}'

    def get_event_id(self):
        return f'control_event__{self.get_id()}'


class Problem():
    def __init__(
        self,
        problem_id: str,
        control_df: pd.DataFrame,
        control_parameter_df: pd.DataFrame,
        objective_observable_df: pd.DataFrame,
        objective_measurement_df: pd.DataFrame,
        start_time: NUMERIC_OR_STRING = 0.0,
    ):
        self.problem_id = problem_id

        self.control_df = control_df
        self.control_parameter_df = control_parameter_df
        self.objective_observable_df = objective_observable_df
        self.objective_measurement_df = objective_measurement_df

        if isinstance(start_time, str):
            if start_time == ESTIMATE:
                raise NotImplementedError(
                    'Estimating the start time is not yet supported.'
                )
            if start_time != LAST_MEASURED_TIMEPOINT:
                raise NotImplementedError(
                    f'Unknown start time: {start_time}'
                )
        else:
            try:
                start_time = float(start_time)
            except TypeError as e:
                raise TypeError(
                    'Please specify a numeric start time or an implemented start time '
                    f'ID. Specified start time: {start_time}'
                ) from e
        self.start_time = start_time

        # FIXME todo checks
        """
        - the parent of estimated parameters has a line in the original
          PEtab parameters table
          - currently redesigned to not have a petab problem stored in this
            class, so would need to be checked independently
        """
        # TODO allow for multiple conditions
        #condition_ids = problem_experimental_conditions(self)
        #if len(condition_ids) != 1:
        #    raise NotImplementedError(
        #        'Multiple experimental conditions in the PEtab control '
        #        'are not yet supported.'
        #    )
        #self.condition_id = one(condition_ids)

    @staticmethod
    def from_yaml(yaml_path: TYPE_PATH) -> 'Problem':
        yaml_path = parse_path(yaml_path)
        petab_path = yaml_path.parent

        with open(yaml_path, 'r') as f:
            yaml_dict = yaml.safe_load(f)

        if len(yaml_dict[PROBLEMS]) != 1:
            raise NotImplementedError(
                'Currently, specification of one and only one control problem '
                'is supported.'
            )
            raise KeyError(
                'Please specify the problem ID when using a specification '
                'with multiple control problems.'
            )
        problem_dict = one(yaml_dict[PROBLEMS])

        if len(problem_dict[CONTROL][CONTROL_FILES]) != 1:
            raise NotImplementedError(
                'Multiple PEtab control, control files are not yet supported.'
            )
        control_df = read_control_df(
            petab_path / one(problem_dict[CONTROL][CONTROL_FILES]),
        )

        if len(problem_dict[CONTROL][CONTROL_PARAMETER_FILES]) != 1:
            raise NotImplementedError(
                'Multiple PEtab control, control parameter files are not yet '
                'supported.'
            )
        control_parameter_df = get_parameter_df(str(
            petab_path / one(problem_dict[CONTROL][CONTROL_PARAMETER_FILES]),
        ))

        if len(problem_dict[OBJECTIVE][OBSERVABLE_FILES]) != 1:
            raise NotImplementedError(
                'Multiple PEtab control, objective observable files are not '
                'yet supported.'
            )
        objective_observable_df = get_observable_df(str(
            petab_path / one(problem_dict[OBJECTIVE][OBSERVABLE_FILES]),
        ))

        if len(problem_dict[OBJECTIVE][MEASUREMENT_FILES]) != 1:
            raise NotImplementedError(
                'Multiple PEtab control, objective measurement files are not '
                'yet supported.'
            )
        objective_measurement_df = get_measurement_df(str(
            petab_path / one(problem_dict[OBJECTIVE][MEASUREMENT_FILES]),
        ))

        start_time = problem_dict[START_TIME]

        return Problem(
            problem_id=problem_dict[PROBLEM_ID],
            control_df=control_df,
            control_parameter_df=control_parameter_df,
            objective_observable_df=objective_observable_df,
            objective_measurement_df=objective_measurement_df,
            start_time=start_time,
        )

    def to_files(self):
        # remove simulation condition ID from
        # - `control_df`
        # - `objective_measurement_df`
        raise NotImplementedError

    @property
    def parameter_df(self) -> pd.DataFrame:
        rows = []
        control_parameter_ids = []
        for _, control_row in self.control_df.iterrows():
            # The estimation problem for all controls with the same
            # control parameter ID must be the same, hence only
            # need to estimate it once.
            if control_row[CONTROL_ID] in control_parameter_ids:
                continue
            control_parameter_ids.append(control_row[CONTROL_ID])

            row = (
                self
                .control_parameter_df.
                loc[control_row[PARAMETER_ID]]
                .copy()
            )
            #row[CONTROL_TARGET] = row.name
            #row[CONTROL_TIME] = control_row[TIME]
            row.name = control_row[CONTROL_ID]
            #row.name = get_control_id(
            #    parameter_id=control_row[PARAMETER_ID],
            #    period_index=index,
            #)
            if control_row[VALUE] == ESTIMATE:
                row[ESTIMATE] = 1
            else:
                row[NOMINAL_VALUE] = float(control_row[VALUE])
                row[ESTIMATE] = 0
            rows.append(row)
        df = pd.DataFrame(data=rows)
        df.index.name = PARAMETER_ID
        df = petab.get_parameter_df(df)
        return df

    @property
    def timecourse(self) -> Timecourse:
        """The controls as a timecourse."""
        # FIXME use as Timecourse property of Problem class
        #periods_dict = {
        #    time: {}
        #    for time in sorted(set([0, *control_df[TIME].values]))
        #}
        start_times = sorted(set([0, *self.control_df[TIME]]))
        periods = []
        for period_index, start_time in enumerate(start_times):
            duration = TIME_STEADY_STATE
            if period_index < len(start_times) - 1:
                duration = start_times[period_index + 1] - start_time
            period = Period(
                duration=duration,
                condition_id=CONTROL_CONDITION_ID,
            )
            periods.append(period)
        timecourse = Timecourse(
            timecourse_id=CONTROL_TIMECOURSE_ID,
            periods=periods,
        )
        return timecourse

    def get_periods_parameters(self, start_period_index: int = 0):
        time = 0
        periods_parameters = []

        #parameter_values = {}
        control_parameters = {}
        """
        Keys are control parameter IDs.
        Values are dictionaries with a required `VALUE` key, and
        an optional `PARAMETER_ID` key if `VALUE == ESTIMATE`.

        Args:
            start_period_index:
                The index that control timecourse periods begin.
                Useful when simulating since some timecourse from the
                original PEtab estimation problem may be prepended to the
                PEtab Control timecourse.
        """

        period_parameters0 = {
            parameter_id: None
            for parameter_id in self.control_parameter_df.index
        }
        for period_index, period in enumerate(self.timecourse.periods):
            period_parameters = period_parameters0.copy()
            for parameter_id in period_parameters:
                updates = self.control_df.loc[
                    (self.control_df[PARAMETER_ID] == parameter_id)
                    & (self.control_df[TIME] == time)
                ]
                if updates.empty:
                    continue
                try:
                    _, update = one(updates.iterrows())
                except ValueError:
                    raise ValueError(
                        'Multiple control parameters are defined for the same '
                        f'parameter and time. Parameter: {parameter_id}. '
                        f'Time: {time}. Controls:\n{updates}'
                    )
                control_id = update[CONTROL_ID]
                if control_id in control_parameters:
                    control_parameters[control_id][PERIODS].append(
                        period_index + start_period_index,
                    )
                    if control_parameters[control_id][VALUE] != update[VALUE]:
                        raise ValueError(
                            'Unexpected error. An update value for a parameter control '
                            'does not match the update value for the same parameter '
                            'control in a different timecourse period. '
                            f'Parameter:\n{control_parameters[control_id]}\n'
                            f'Update:\n{update}'
                        )
                    # TODO assert the lowest period index is used for the control
                    # parameter ID?
                else:
                    control_parameters[control_id] = {
                        VALUE: update[VALUE],
                        PERIODS: [period_index + start_period_index],
                        PARAMETER_ID: parameter_id,
                    }
                period_parameters[parameter_id] = control_id
            time += period.duration
            periods_parameters.append(period_parameters)
        return periods_parameters, control_parameters

#    def setup_simulator(
#        self,
#        simulator_class: Simulator,
#        petab_problem: petab.Problem,
#        timecourse_id: str = None,
#        default_problem_parameters: Dict[str, float] = None,
#        model_settings: Dict[str, Any] = None,
#        solver_settings: Dict[str, Any] = None,
#        fix_petab_problem_parameters: Dict[str, float] = None,
#    ):
#        """Setup a timecourse simulator to solve the control problem.
#
#        Args:
#            simulator_class:
#                The simulator class to use. Should inherit from
#                `petab_timecourse.Simulator`.
#            petab_problem:
#                The original PEtab problem.
#            timecourse_id:
#                The ID of the timecourse in the original PEtab problem to use.
#            default_problem_parameters:
#                All parameters must have some value for each timecourse period,
#                for all periods in the original PEtab problem, and the control
#                problem. Default values for missing parameters can be provided
#                here. Keys are parameter IDs, values are parameter values.
#            fix_petab_problem_parameters:
#                Keys are parameters IDs in `petab_problem.parameter_df`,
#                values are parameter values. The PEtab problems used by the
#                simulator and optimizer will fix these parameters
#                (i.e. they won't be estimated). Parameter values are expected
#                to be on linear scale.
#            model_settings:
#                Keys are AMICI model setters (e.g. `setAlwaysCheckFinite`)
#                and values are supplied to the setters.
#            solver_settings:
#                Keys are AMICI solver setters (e.g. `setAbsoluteTolerance`)
#                and values are supplied to the setters.
#        """
#        if default_problem_parameters is None:
#            default_problem_parameters = {}
#
#        for parameter_id, parameter_value in default_problem_parameters.items():
#            default_problem_parameters[parameter_id] = \
#                petab.to_float_if_float(parameter_value)
#
#        petab_problem = copy.deepcopy(petab_problem)
#
#        if fix_petab_problem_parameters is None:
#            fix_petab_problem_parameters = {}
#        for parameter_id, parameter_value in fix_petab_problem_parameters.items():
#            petab_problem.parameter_df.loc[parameter_id, [
#                NOMINAL_VALUE,
#                ESTIMATE,
#            ]] = [
#                parameter_value,
#                0,
#            ]
#
#        self.simulator_control_petab_problem = \
#            get_control_petab_problem(
#                petab_control_problem=self,
#                petab_problem=petab_problem,
#                timecourse_id=timecourse_id,
#            )
#
#        self.optimizer_control_petab_problem = copy.deepcopy(
#            self.simulator_control_petab_problem
#        )
#        self.optimizer_control_petab_problem.parameter_df = (
#            pd.concat([
#                petab_problem.parameter_df.copy(),
#                self.parameter_df,
#            ])
#        )
#
#        self.simulator_control_petab_problem.parameter_df = (
#            pd.concat([
#                petab_problem.parameter_df.copy(),
#                self.control_parameter_df,
#            ])
#        )
#
#        self.simulator = simulator_class(
#            petab_problem=self.simulator_control_petab_problem,
#            timecourse_id=CONTROL_TIMECOURSE_ID,
#        )
#
#        # FIXME check whether explicit specification of `plist` is important
#        #if self.simulator.amici_model is None:
#        #    raise ValueError(
#        #        'Simulator must have an AMICI model, to set '
#        #        'sensitivities correctly.'
#        #    )
#        #sensitivity_parameters = {
#        #    parameter_id: (
#        #        self
#        #        .simulator
#        #        .amici_model
#        #        .getParameterIds()
#        #        .index(parameter_id)
#        #    )
#        #    for parameter_id in self.simulator_control_petab_problem.x_free_ids
#        #}
#
#        #for amici_edata in self.simulator.amici_edata_periods:
#        #    amici_edata.plist = list(sensitivity_parameters.values())
#
#        original_conditions = {
#            original_condition_id: dict(
#                petab_problem
#                .condition_df
#                .loc[original_condition_id]
#            )
#            for original_condition_id in set(
#                period.condition_id
#                for period in Timecourse.from_df(
#                    timecourse_df=petab_problem.timecourse_df,
#                    timecourse_id=timecourse_id,
#                ).periods
#            )
#        }
#        if CONTROL_CONDITION_ID in original_conditions:
#            raise ValueError(
#                'Please reimplement the PEtab problem to not have a condition with '
#                f'ID: {CONTROL_CONDITION_ID}'
#            )
#        original_conditions[CONTROL_CONDITION_ID] = {}
#
#        # Replace fixed condition parameters with their values.
#        fixed_original_conditions = {
#            condition_id: {
#                k: fix_petab_problem_parameters.get(v, v)
#                for k, v in condition.items()
#            }
#            for condition_id, condition in original_conditions.items()
#        }
#        unreplaced_ids_in_conditions = set.union(*[
#            set([
#                value
#                for value in condition.values()
#                if isinstance(value, str)
#            ])
#            for condition in fixed_original_conditions.values()
#        ])
#        if unreplaced_ids_in_conditions:
#            raise ValueError(
#                "Please supply replacements for any IDs that appear in the "
#                f"original conditions. Unreplaced IDs: {unreplaced_ids_in_conditions}"
#            )
#        # Replace fixed parameter mapping parameters with their values.
#        self.simulator.replace_in_parameter_mapping(
#            replacements=fix_petab_problem_parameters,
#            scaled=False,
#        )
#        # FIXME check if any parameters remain
#
#        simulator_periods_parameters, _ = \
#            self.get_periods_parameters()
#
#        len_original_timecourse = (
#            len(self.simulator.timecourse.periods)
#            - len(self.timecourse.periods)
#        )
#
#        _, self.simulator_control_parameters = \
#            self.get_periods_parameters(
#                start_period_index=len_original_timecourse,
#            )
#
#        self.simulator_default_problem_parameters_periods = [
#            {
#                **default_problem_parameters,
#                **fixed_original_conditions[period.condition_id],
#                # FIXME assumes the control timecourse always appears after the
#                #       original timecourse
#                **(
#                    simulator_periods_parameters[
#                        period_index - len_original_timecourse
#                    ]
#                    if period_index - len_original_timecourse >= 0
#                    else {}
#                ),
#            }
#            for period_index, period in enumerate(
#                self.simulator.timecourse.periods
#            )
#        ]
#
#        if model_settings is not None:
#            for setter, value in model_settings.items():
#                getattr(self.simulator.amici_model, setter)(value)
#
#        if solver_settings is not None:
#            for setter, value in solver_settings.items():
#                getattr(self.simulator.amici_solver, setter)(value)
#
#    def simulate(
#        self,
#        problem_parameters: Dict[str, float],
#    ):
#        """Simulate the timecourse for a control problem.
#
#        All parameters that appear in any timecourse period condition
#        should have at least default values in for all timecourse periods.
#        i.e. the problem parameters should be a list of dictionaries where
#        all dictionaries have the same keys.
#
#        Args:
#            problem_parameters:
#                Values to substitute in for estimated control parameters,
#                on parameter scale.
#        """
#        # Copy to avoid overwriting user's object.
#        problem_parameters_periods = copy.deepcopy(
#            self.simulator_default_problem_parameters_periods
#        )
#
#        for period_index, problem_parameters_period in enumerate(problem_parameters_periods):
#            for parameter_id, parameter_value in problem_parameters_period.items():
#                # Use the provided value for the control parameter
#                if (
#                    isinstance(parameter_value, str)
#                    and parameter_value in problem_parameters
#                ):
#                    if parameter_id in problem_parameters:
#                        warnings.warn(
#                            f'The parameter `{parameter_id}` takes the value of '
#                            f'the control parameter `{parameter_value}` (period '
#                            f'index: {period_index}). However, values for both the '
#                            'parameter and the control parameter were provided. '
#                            'The value for the control parameter will be used.'
#                        )
#                    parameter_value = problem_parameters[parameter_value]
#                # Else use the provided value for the corresponding
#                # parameter
#                elif parameter_id in problem_parameters:
#                    parameter_value = problem_parameters[parameter_id]
#                # Else use the default value provided to `setup_simulator`
#                elif isinstance(parameter_value, float):
#                    pass
#                # Else use the default value for the
#                # control parameter
#                elif (
#                    isinstance(parameter_value, str)
#                    and isinstance(
#                        (
#                            self
#                            .simulator_control_parameters
#                            [parameter_value]
#                            [VALUE]
#                        ),
#                        float,
#                    )
#                ):
#                    parameter_value = (
#                        self
#                        .simulator_control_parameters
#                        [parameter_value]
#                        [VALUE]
#                    )
#                # Else use nominal value from the control
#                # parameters table, for the corresponding parameter
#                elif not np.isnan(
#                    self
#                    .control_parameter_df
#                    .loc[
#                        self
#                        .simulator_control_parameters
#                        [parameter_value]
#                        [PARAMETER_ID]
#                    ]
#                    [NOMINAL_VALUE]
#                ):
#                    parameter_value = (
#                        self
#                        .control_parameter_df
#                        .loc[
#                            self
#                            .simulator_control_parameters
#                            [parameter_value]
#                            [PARAMETER_ID]
#                        ]
#                        [NOMINAL_VALUE]
#                    )
#                # Else fail
#                else:
#                    breakpoint()
#                    raise ValueError(
#                        'Please supply a value for the control parameter '
#                        f'`{parameter_value}` (instance of parameter `{parameter_id}`). '
#                        'This can be supplied in multiple ways, for example, '
#                        'as a key-value pair in the `problem_parameters` '
#                        'argument of this method.'
#                    )
#                problem_parameters_periods[period_index][parameter_id] = \
#                    parameter_value
#
#        periods_results = self.simulator.simulate(
#            problem_parameters_periods=problem_parameters_periods,
#            scaled_parameters=True,
#            control_parameters=self.simulator_control_parameters,
#        )
#
#        llh = sum(period_results[LLH] for period_results in periods_results)
#        sllh = {}
#        for control_parameter_id, control_description in self.simulator_control_parameters.items():
#            sllh[control_parameter_id] = sum(
#                period_results[SLLH][control_description[PARAMETER_ID]]
#                for period_index, period_results in enumerate(periods_results)
#                if period_index in control_description[PERIODS]
#            )
#
#        results = {
#            LLH: llh,
#            SLLH: sllh,
#            PERIODS_RESULTS: periods_results,
#        }
#
#        return results


def get_period_id(period_index: int, time: float):
    return f'period_{period_index}_{time}'


def get_control_events_petab_problem(
    petab_control_problem: Problem,
    petab_problem: petab.Problem,
) -> petab.Problem:
    petab_problem = copy.deepcopy(petab_problem)

    start_time = petab_control_problem.start_time
    if petab_control_problem.start_time == LAST_MEASURED_TIMEPOINT:
        start_time = petab_problem.measurement_df[TIME].max()

    sbml_model = petab_problem.sbml_model
    petab_problem.sbml_model.setId(
        f'{petab_problem.sbml_model.getId()}__control_events_petab_problem'
    )

    # Generate control and switch parameters
    parameter_controls = {}
    for _, row in petab_control_problem.control_df.iterrows():
        parameter_id = row[PARAMETER_ID]
        parameter_control = ParameterControl(
            parameter_id=parameter_id,
            value=row[VALUE],
            time=row[TIME] + start_time,
        )
        if parameter_id in parameter_controls:
            parameter_controls[parameter_id].append(parameter_control)
        else:
            parameter_controls[parameter_id] = [parameter_control]

    for parameter_id, controls in parameter_controls.items():
        for control in controls:
            value = control.value
            if value == ESTIMATE:
                value = DUMMY_VALUE
            add_parameter(
                sbml_model,
                control.get_control_parameter_id(),
                value,
            )
            add_parameter(
                sbml_model,
                control.get_switch_parameter_id(),
                ZERO,
                constant=False,
            )

    # FIXME move to different file as function...
    for parameter_id, controls in parameter_controls.items():
        for control in controls:
            event_id = control.get_event_id()
            offset_control_time = control.time + start_time
            trigger_formula = f'time >= {offset_control_time}'
            variable = control.target_id
            event_assignment_formula = control.value
            if control.value == ESTIMATE:
                event_assignment_formula = control.get_control_parameter_id()

            event = sbml_model.createEvent()
            event.setId(event_id)
            event.setUseValuesFromTriggerTime(True)

            trigger = event.createTrigger()
            trigger.setInitialValue(True)
            trigger.setPersistent(True)
            trigger_math = libsbml.parseL3Formula(trigger_formula)
            trigger.setMath(trigger_math)

            event_assignment = event.createEventAssignment()
            event_assignment.setVariable(variable)
            event_assignment_math = \
                libsbml.parseL3Formula(str(event_assignment_formula))
            event_assignment.setMath(event_assignment_math)
    # END FIXME


    parameter_df = parameter_controls_to_parameter_df(
        parameter_controls,
        # FIXME currently, the estimation problem of control parameters is
        #       set to the estimation problem for the parent parameter.
        #       Add `controlParameterId` to the controls table to manually
        #       specify the IDs that control parameters should take, s.t.
        #       a PEtab parameters table for the estimation of these
        #       parameters can also be individually specified.
        petab_control_problem.control_parameter_df,
    )

    condition_df, parameter_df, timecourse_df = \
        parameter_controls_to_timecourse_new(
            # FIXME use kwargs
            parameter_controls,
            petab_problem,
            petab_control_problem,
        )

    petab_problem.condition_df = condition_df
    petab_problem.measurement_df = petab_control_problem.objective_measurement_df
    petab_problem.parameter_df = parameter_df
    petab_problem.observable_df = petab_control_problem.objective_observable_df
    petab_problem.timecourse_df = timecourse_df

    petab_problem.measurement_df[TIME] += start_time

    return petab_problem

def get_control_petab_timecourse_problem(
    petab_control_problem: Problem,
    petab_problem: petab.Problem,
) -> petab.Problem:
    petab_problem = copy.deepcopy(petab_problem)

    start_time = petab_control_problem.start_time
    if petab_control_problem.start_time == LAST_MEASURED_TIMEPOINT:
        start_time = petab_problem.measurement_df[TIME].max()

    petab_problem.sbml_model.setId(
        f'{petab_problem.sbml_model.getId()}__control_petab_timecourse_problem'
    )

    # Generate control and switch parameters
    parameter_controls = {}
    for _, row in petab_control_problem.control_df.iterrows():
        parameter_id = row[PARAMETER_ID]
        parameter_control = ParameterControl(
            parameter_id=parameter_id,
            value=row[VALUE],
            time=row[TIME] + start_time,
        )
        if parameter_id in parameter_controls:
            parameter_controls[parameter_id].append(parameter_control)
        else:
            parameter_controls[parameter_id] = [parameter_control]

    condition_df, parameter_df, timecourse_df = \
        parameter_controls_to_timecourse_new(
            # FIXME use kwargs
            parameter_controls,
            petab_problem,
            petab_control_problem,
        )

    petab_problem.condition_df = condition_df
    petab_problem.measurement_df = petab_control_problem.objective_measurement_df
    petab_problem.parameter_df = parameter_df
    petab_problem.observable_df = petab_control_problem.objective_observable_df
    petab_problem.timecourse_df = timecourse_df

    petab_problem.measurement_df[TIME] += start_time

    return petab_problem

def get_control_petab_problem(
    petab_control_problem: Problem,
    petab_problem: petab.Problem,
    timecourse_id: str,
) -> petab.Problem:
    petab_problem = copy.deepcopy(petab_problem)

    start_time = petab_control_problem.start_time
    if petab_control_problem.start_time == LAST_MEASURED_TIMEPOINT:
        start_time = petab_problem.measurement_df[TIME].max()

    petab_problem.sbml_model.setId(
        f'{petab_problem.sbml_model.getId()}__control_petab_problem'
    )

    problem_parameter_period_dicts = {
        condition_id: dict(condition)
        for condition_id, condition in petab_problem.condition_df.iterrows()
    }

    control_timecourse = petab_control_problem.timecourse

    # generate parameter table to estimate timecourse parameters
    # in all periods where they are indicated to be estimated in the `controls.tsv`
    # file
    #control_parameter_df = petab_control_problem.parameter_df

    estimate_timecourse = Timecourse.from_df(
        timecourse_df=petab_problem.timecourse_df,
        timecourse_id=timecourse_id,
    )
    original_condition_ids = set(
        period.condition_id
        for period in estimate_timecourse.periods
    )
    '''
    original_conditions = {
        original_condition_id: dict(petab_problem.condition_df.loc[original_condition_id])
        for original_condition_id in original_condition_ids
    }
    '''

    condition_df = pd.concat([
        copy.deepcopy(petab_problem.condition_df),
        pd.Series(name=CONTROL_CONDITION_ID).to_frame().T,
        pd.Series(name=CONTROL_TIMECOURSE_ID).to_frame().T,
    ])
    condition_df.index.name = CONDITION_ID
    #breakpoint()

    full_timecourse = Timecourse.from_timecourses(
        timecourses=[estimate_timecourse, control_timecourse],
        durations=[start_time],
        timecourse_id=CONTROL_TIMECOURSE_ID,
    )
    full_timecourse_df = full_timecourse.to_df()

    petab_problem.condition_df = condition_df.copy()
    petab_problem.measurement_df = \
        petab_control_problem.objective_measurement_df.copy()
    petab_problem.observable_df = \
        petab_control_problem.objective_observable_df.copy()
    petab_problem.timecourse_df = full_timecourse_df.copy()

    original_parameter_df = petab_problem.parameter_df.copy()
    original_parameter_df[ESTIMATE] = 0
    petab_problem.parameter_df = original_parameter_df
    #petab_problem.parameter_df = pd.concat([
    #    original_parameter_df,
    #    petab_control_problem.parameter_df,
    #])

    petab_problem.measurement_df[TIME] += start_time
    petab_problem.measurement_df[SIMULATION_CONDITION_ID] = \
        CONTROL_TIMECOURSE_ID

    petab_problem.parameter_df = (
        pd.concat([
            petab_problem.parameter_df.copy(),
            petab_control_problem.parameter_df,
        ])
    )

    return petab_problem

    #return (
    #    petab_problem,
    #    original_conditions,
    #    #control_parameter_df,
    #)
