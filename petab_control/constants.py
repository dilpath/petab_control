from pathlib import Path
from typing import Union

PARAMETER = 'parameter'
SPECIES = 'species'
STATE = 'state'

ESTIMATE = 'estimate'
DUMMY_VALUE = 0.1
ZERO = 0

TYPE_PATH = Union[str, Path]
#PATH_LIKE = TYPE_PATH  # FIXME remove

CONTROL = 'control'
OBJECTIVE = 'objective'

PROBLEMS = 'problems'
PROBLEM_ID = 'problem_id'
START_TIME = 'start_time'

VALUE = 'value'

CONTROL_FILES = 'control_files'
CONTROL_PARAMETER_FILES = 'control_parameter_files'
from petab.C import (
    MEASUREMENT_FILES,
    OBSERVABLE_FILES,
)

LAST_MEASURED_TIMEPOINT = 'last_measured_timepoint'

# TODO WIP For a combined original+control PEtab problem
CONTROL_TIME = 'control_time'
CONTROL_TARGET = 'control_target'
CONTROL_VALUE = 'control_value'

CONTROL_ID = 'control_id'

CONTROL_CONDITION_ID = 'control_condition_id'
CONTROL_TIMECOURSE_ID = 'control_timecourse_id'

PERIODS = 'periods'
PERIODS_RESULTS = 'periods_results'

CATEGORY = 'category'
# FIXME better name for the original PEtab problem without optimal control
# added to it?
ORIGINAL = 'original'
