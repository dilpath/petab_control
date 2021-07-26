from pathlib import Path
from typing import Union

PARAMETER = 'parameter'
SPECIES = 'species'
STATE = 'state'

ESTIMATE = 'estimate'
#DEFAULT_VALUE = 0.0
DUMMY_VALUE = 0.1
ZERO = 0

PATH_LIKE = Union[str, Path]

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
