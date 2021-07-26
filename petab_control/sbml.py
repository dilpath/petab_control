import libsbml

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
