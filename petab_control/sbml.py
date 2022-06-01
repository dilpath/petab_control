import libsbml

from .constants import TYPE_PATH, PARAMETER


def add_parameter(
    sbml_model: libsbml.Model,
    parameter_id: str,
    initial_value: float,
    constant: bool = True,
):

    parameter = sbml_model.createParameter()
    parameter.setId(parameter_id)
    parameter.setValue(initial_value)
    parameter.setConstant(constant)


def add_assignment_rule(
    sbml_model: libsbml.Model,
    target_id: str,
    formula: str,
    fix_parameter_definition: bool = True,
):
    rule = sbml_model.createAssignmentRule()
    rule.setVariable(target_id)
    rule.setMath(libsbml.parseL3Formula(formula))
    if fix_parameter_definition:
        sbml_model.getParameter(target_id).setConstant(False)


# FIXME request that users only supply SBML where the control parameters are already not constant?
# FIXME move this method to petab_timecourse and instead change the `petab_control` method to just provide the IDs that need to be set not constant?
def set_control_parameters_not_constant(
    petab_control_problem: 'petab_control.Problem',
    petab_problem: 'petab.Problem',
) -> None:

    for parameter_id in petab_control_problem.control_parameter_df.index:
        parameter = petab_problem.sbml_model.getElementBySId(parameter_id)
        # Perhaps misuse of this constant `PARAMETER`, currently means two things:
        #    - a parameter in the control problem
        #    - a parameter in the SBML model
        if parameter.getElementName() != PARAMETER:
            raise ValueError(
                'A control parameter was specified that is not an SBML parameter. '
                'Control parameter ID: {parameter_id}'
            )
        if parameter.setConstant(False) != 0:
            raise ValueError(
                'An unexpected error occurred while trying to set the control '
                'parameter as not constant in the SBML model. Control parameter ID: '
                f'{parameter_id}'
            )
