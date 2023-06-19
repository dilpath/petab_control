# PEtab control: a PEtab extension for optimal control problems.

- the time of objective measurements and controls are expected to be relative to the `start_time` of the control problem
  - i.e., for 20 time units after the last measurement timepoint of the original PEtab problem
    - set `20` as the time in the objective measurements or controls table
    - set `last_measured_timepoint` as the `start_time` in the PEtab Control YAML file

# File format
## Control parameters
This is a PEtab parameters table, for the parameters that act as controls in the model.
## Controls
A TSV file that defines the times at which the control parameters can take different values.

| `control_id`  | `parameterId`     | `time`   | `value`                                       |
|----------------------|------------------|------------|--------------------------------------------------------|
| (Unique) [string]    | [string]         | [float] OR [; delimited list of float]  | [string/float] |

- `control_id`: An ID for the control.
- `parameterId`: The control parameter.
- `time`: The control parameter takes the control value at these time(s).
- `value`: The control value, either fixed to some `float` value, or specified to be estimated with `estimate`. If `estimate`, this value will be estimated according to the control parameter, but independently of other controls that use the same control parameter.

## Objective measurements
A PEtab measurements table. The times and values are the target for the optimal control problem. e.g., if you want to see a value of "50" at time "25", create such a measurement here.

## Objective observables
A PEtab observables table, for the corresponding objective measurements. The noise model can be used to priotize targets.

## PEtab Control YAML file
Groups all files together.

```yaml
problems:
  - problem_id: ...
    start_time: ...
    timecourseId: ...
    control:
      control_files:
        - ...
      control_parameter_files:
        - ...
    objective:
      measurement_files:
        - ...
      observable_files:
        - ...
```

The YAML contains a list of optimal control `problems`. Each problem has:
- `problem_id`: An ID for the optimal control problem.
- `start_time`: An offset for all times in the optimal control problem.
- `timecourseId`: The timecourse that will be controlled.
- `control_files`: The "Controls" TSV files.
- `control_parameter_files`: The "Control parameters" TSV files.
- `measurement_files`: The "Objective measurements" TSV files.
- `observable_files`: The "Objective observables" TSV files.


# TODO 
- if there is an `inf` time point in the 
- timecourses with multiple equilibrations are possible
  - if a measurement has multiple equilibrations, all measurement times should be noted with the following syntax
    - `{EQUILIBRATION_INDEX}:{TIME}` instead of `{TIME}`
    - alternative: `{PERIOD_INDEX}:{TIME RELATIVE TO PERIOD OR LAST EQUILIBRATION?}`
