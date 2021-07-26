import abc
import copy
from typing import Sequence, Union

import libsbml
from more_itertools import one
import pandas as pd
import petab
from petab import (
    get_measurement_df,
    get_observable_df,
    get_parameter_df,
)
from petab.C import (
    PARAMETER_ID,
    TIME,
)
# FIXME rename to `slugify` convention?
from petab_timecourse.sbml import get_slug as slugify
import yaml

from .constants import (
    #DEFAULT_VALUE,
    DUMMY_VALUE,
    ZERO,
    ESTIMATE,
    PARAMETER,
    STATE,

    PATH_LIKE,

    PROBLEMS,
    CONTROL,
    PROBLEM_ID,
    START_TIME,
    CONTROL_FILES,
    OBJECTIVE,
    CONTROL_PARAMETER_FILES,
    MEASUREMENT_FILES,
    OBSERVABLE_FILES,

    LAST_MEASURED_TIMEPOINT,
    VALUE,
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
    parameter_controls_to_timecourse,
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


#class Control():
#    def __init__(
#        self,
#        target: Target,
#        values: Values,
#    ):
#        self.target = target
#        self.values = values
#
#        self.parameter_ids = []
#        self.switch_ids = []
#
#    def add_timepoint(
#        self,
#        timepoint: NUMERIC,
#        #parameter_id: str,
#        #switch_id: str,
#        #value: NUMERIC_OR_STRING,
#    ):
#        target_id = self.target.target_id
#        parameter_id = f'control_parameter__{target_id}__{get_slug(timepoint)}'
#        switch_id = f'control_switch__{target_id}__{get_slug(timepoint)}'
#        self.parameter_ids.append(parameter_id)
#        self.switch_ids.append(switch_id)
#
#    def get_formula(
#        self,
#    ):
#        formula = ' + '.join([
#            f'{switch_id}*{parameter_id}'
#            for switch_id, parameter_id
#            in zip(self.switch_ids, self.parameter_ids)
#        ])
#        return formula


class Control():
    def __init__(
        self,
        target_id: str,
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

        #self.parameter_ids = []
        #self.switch_ids = []

    #def add_timepoint(
    #    self,
    #    timepoint: NUMERIC,
    #    #parameter_id: str,
    #    #switch_id: str,
    #    #value: NUMERIC_OR_STRING,
    #):
    #    target_id = self.target.target_id
    #    parameter_id = f'control_parameter__{target_id}__{get_slug(timepoint)}'
    #    switch_id = f'control_switch__{target_id}__{get_slug(timepoint)}'
    #    self.parameter_ids.append(parameter_id)
    #    self.switch_ids.append(switch_id)

    #def get_formula(
    #    self,
    #):
    #    formula = ' + '.join([
    #        f'{switch_id}*{parameter_id}'
    #        for switch_id, parameter_id
    #        in zip(self.switch_ids, self.parameter_ids)
    #    ])
    #    return formula


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


class Objective(Control):
    pass


class Problem():
    def __init__(
        self,
        problem_id: str,
        #timepoint0: Union[float, int],
        #timepoints: Timepoints,
        #controls: Sequence[Control],
        #objectives: Sequence[Objective],
        control_df: pd.DataFrame,
        control_parameter_df: pd.DataFrame,
        objective_observable_df: pd.DataFrame,
        objective_measurement_df: pd.DataFrame,
        start_time: NUMERIC_OR_STRING = 0.0,
        petab_problem: petab.Problem = None,
    ):
        self.problem_id = problem_id
        #self.timepoint0 = timepoint0
        #self.timepoints = timepoints
        #self.controls = controls
        #self.objectives = objectives

        self.control_df = control_df
        self.control_parameter_df = control_parameter_df
        self.objective_observable_df = objective_observable_df
        self.objective_measurement_df = objective_measurement_df
        self.petab_problem = petab_problem

        if isinstance(start_time, str):
            if start_time == ESTIMATE:
                raise NotImplementedError(
                    'Estimating the start time is not yet supported.'
                )
            elif start_time != LAST_MEASURED_TIMEPOINT:
                raise NotImplementedError(
                    f'Unknown start time: {start_time}'
                )
        self.start_time = start_time

        # FIXME todo checks
        """
        - the parent of estimated parameters has a line in the original
          PEtab parameters table
        -
        """
        # TODO allow for multiple conditions
        condition_ids = problem_experimental_conditions(self)
        if len(condition_ids) != 1:
            raise NotImplementedError(
                'Multiple experimental conditions in the PEtab control '
                'are not yet supported.'
            )
        self.condition_id = one(condition_ids)

    @staticmethod
    def from_yaml(
        yaml_path: PATH_LIKE,
        petab_problem: petab.Problem = None,
    ) -> 'Problem':
        yaml_path = parse_path(yaml_path)
        petab_path = yaml_path.parent

        if petab_problem is None:
            raise NotImplementedError(
                'PEtab control currently only supports use with a single '
                'PEtab problem, which must be supplied to this method.'
            )

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
            petab_problem=petab_problem,
        )

    #def get_estimated_parameter(
    #    self,
    #    target_id,
    #    timepoint,
    #):
    #    parameter_id = f'control_parameter_{target_id}_{get_slug(timepoint)}'
    #    return parameter_id

    #def estimated_parameters(self) -> Sequence[str]:
    #    for control in self.controls:
    #        if control.target.target_type != PARAMETER:
    #            raise NotImplementedError
    #        target_id = control.target.target_id
    #        control_parameters = [
    #            get_control_parameter(target_id, timepoint)
    #            for timepoint in self.timepoints
    #        ]

    def get_control_petab_problem(
        self,
    ) -> petab.Problem:
        petab_problem = copy.deepcopy(self.petab_problem)
        sbml_document = petab_problem.sbml_document
        sbml_model = sbml_document.getModel()

        # Generate control and switch parameters
        parameter_controls = {}
        #parameter_controls_list = []
        for row_index, row in self.control_df.iterrows():
            parameter_id = row[PARAMETER_ID]
            parameter_control = ParameterControl(
                parameter_id=parameter_id,
                value=row[VALUE],
                time=row[TIME],
            )
            #parameter_controls_list.append(
            #    ParameterControl(
            #        parameter_id=parameter_id,
            #        value=row[VALUE],
            #        time=row[TIME],
            #    )
            #)
            if parameter_id in parameter_controls:
                parameter_controls[parameter_id].append(parameter_control)
            else:
                parameter_controls[parameter_id] = [parameter_control]

        #parameter_ids = []
        #parameter_values = []
        #switch_ids = []
        #for control in self.controls:
        #    for timepoint in self.timepoints:
        #        control.add_timepoint(timepoint)
        #    parameter_ids.extend(control.parameter_ids)
        #    parameter_values.extend(control.values)
        #    switch_ids.extend(control.switch_ids)

        # Generate parameter assignment rule with generated parameters
        #parameter_assignment_rules = {}
        #for control in self.controls:
        #    parameter_assignment_rules[control.target.target_id] = \
        #        control.get_formula()
        parameter_assignment_rules = \
            parameter_controls_to_formulae(parameter_controls)

        # Add parameters and assignment rules to SBML
        #for id, value in zip(parameter_ids, parameter_values):
        #    if value == ESTIMATE:
        #        add_parameter(sbml_model, id, DEFAULT_VALUE)
        #    else:
        #        add_parameter(sbml_model, id, value)
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

        #for id in switch_ids:
        #    add_parameter(sbml_model, id, DEFAULT_VALUE)

        for parameter_id, formula in parameter_assignment_rules.items():
            add_assignment_rule(sbml_model, parameter_id, formula)

        parameter_df = parameter_controls_to_parameter_df(
            parameter_controls,
            # FIXME currently, the estimation problem of control parameters is
            #       set to the estimation problem for the parent parameter.
            #       Add `controlParameterId` to the controls table to manually
            #       specify the IDs that control parameters should take, s.t.
            #       a PEtab parameters table for the estimation of these
            #       parameters can also be individually specified.
            self.control_parameter_df,
        )

        #timecourse_related_dfs = parameter_controls_to_timecourse(
        condition_df, timecourse_df = parameter_controls_to_timecourse(
            parameter_controls,
            self.petab_problem,
            self,
        )

        petab_problem.condition_df = condition_df
        petab_problem.measurement_df = self.objective_measurement_df
        petab_problem.parameter_df = parameter_df
        petab_problem.observable_df = self.objective_observable_df
        petab_problem.timecourse_df = timecourse_df
        #print(timecourse_related_dfs)
        #breakpoint()

        ## Add parameters to conditions table files, and generate timecourse
        #condition_df = get_switch_condition_df(switch_ids)
        ##condition_dfs = []
        ##for index, switch_id in enumerate(switch_ids):
        ##    condition_dfs.append(get_condition_table(
        ##        target_id=switch_id,
        ##        target_values=[0,1]
        ##    ))

        ## Generate measurements table for desired objective
        ## Output control PEtab problem to files
        return petab_problem
