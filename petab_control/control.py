#class Control():
#    def __init__(
#        self,
#        target_id: str,
#        time: NUMERIC_OR_STRING,
#        value: NUMERIC_OR_STRING,
#    ):
#        self.target_id = target_id
#        self.time = time
#        self.value = value
#
#    def get_id(self) -> str:
#        return (
#            f'target__{self.target_id}' + '__'
#            f'time__{slugify(self.time)}' + '__'
#            f'value__{slugify(self.value)}'
#        )
#
#
#class ParameterControl(Control):
#    def __init__(
#        self,
#        parameter_id: str,
#        *args,
#        **kwargs,
#    ):
#        super().__init__(
#            target_id=parameter_id,
#            *args,
#            **kwargs
#        )
#
#    def get_control_parameter_id(self):
#        return f'control_parameter__{self.get_id()}'
#
#    def get_switch_parameter_id(self):
#        return f'switch_parameter__{self.get_id()}'
#
#    def get_control_condition_id(self):
#        return f'control_condition__{self.get_id()}'
#
#
#import pandas as pd
#
#
#def get_control_id(row: pd.Series):
#    return (
#        f'target__{row.parameter_id}' + '__'
#        f'time__{slugify(row.time)}' + '__'
#        f'value__{slugify(row.value)}'
#    )
#
#
#def get_control_parameter_id(row: pd.Series):
#    return f'control_parameter__{get_control_id(row)}'
#
#
#def get_switch_parameter_id(row: pd.Series):
#    return f'switch_parameter__{get_control_id(row)}'
#
#
#def get_control_condition_id(row: pd.Series):
#    return f'control_condition__{get_control_id(row)}'
