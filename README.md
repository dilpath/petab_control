# PEtab control: a PEtab extension for optimal control problems.

- the time of objective measurements and controls are expected to be relative to the `start_time` of the control problem
  - i.e., for 20 time units after the last measurement timepoint of the original timepoint
    - set `20` as the time in the objective measurements or controls table
    - set `last_measured_timepoint` as the `start_time` in the PEtab Control YAML file

# TODO 
- if there is an `inf` time point in the 
- timecourses with multiple equilibrations are possible
  - if a measurement has multiple equilibrations, all measurement times should be noted with the following syntax
    - `{EQUILIBRATION_INDEX}:{TIME}` instead of `{TIME}`
    - alternative: `{PERIOD_INDEX}:{TIME RELATIVE TO PERIOD OR LAST EQUILIBRATION?}`
