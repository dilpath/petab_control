# 1. Import problem
import petab
import petab_timecourse

petab_problem0 = petab_timecourse.Problem.from_yaml(
    'input/optimize_then_control/petab/estimate/petab_problem.yaml',
)
petab_problem0.model = petab.models.sbml_model.SbmlModel(
    petab_timecourse.sbml.add_timecourse_as_events(
        petab_problem=petab_problem0,
        timecourse_id="timecourse1",
    )
)
petab_problem0.extensions_config = None

# 2. Optimize original problem
import pypesto.petab
import pypesto.optimize

pypesto_importer0 = pypesto.petab.PetabImporter(petab_problem0)
pypesto_problem0 = pypesto_importer0.create_problem()
pypesto_engine = pypesto.engine.MultiProcessEngine(7)
pypesto_result0 = pypesto.optimize.minimize(pypesto_problem0, filename=None, n_starts=20, engine=pypesto_engine)
unscaled_parameters0 = petab_problem0.unscale_parameters(dict(zip(
    pypesto_problem0.x_names,
    pypesto_result0.optimize_result.list[0].x
)))

# 3. Setup controlled problem
import petab
import petab_control
import petab_timecourse

petab_control_problem = petab_control.Problem.from_yaml(
    yaml_path='input/optimize_then_control/petab/control/petab_control_problem.yaml',
)
petab_problem = petab_control.get_control_events_petab_problem(
    petab_control_problem=petab_control_problem,
    petab_problem=petab_problem0,
    unscaled_parameters0=unscaled_parameters0,
    timecourse_id='timecourse1',
)

# 4. Optimize controlled problem
pypesto_importer = pypesto.petab.PetabImporter(petab_problem)
pypesto_problem = pypesto_importer.create_problem()
pypesto_result = pypesto.optimize.minimize(pypesto_problem, filename=None, n_starts=20, engine=pypesto_engine)

# 5. Print solution
optimal_parameters = petab_problem.unscale_parameters(dict(zip(pypesto_problem.x_names, pypesto_result.optimize_result.list[0].x)))
print(optimal_parameters)
