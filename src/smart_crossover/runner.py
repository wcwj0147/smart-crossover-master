"""Module of a runner for experiments."""
from typing import Union, Optional

import gurobipy

from smart_crossover.output import Output
from smart_crossover.lp_methods.algorithms import run_perturb_algorithm
from smart_crossover.solver_caller.caller import SolverCaller, SolverSettings
from smart_crossover.solver_caller.solving import generate_solver_caller


# Todo: separate into NetworkExperimentRunner & LPExperimentRunner.
class ExperimentRunner:
    models: list[Union[gurobipy.Model]]
    solver: str
    solver_caller: SolverCaller
    solver_settings: SolverSettings
    results: dict[str, list[Output]]

    def __init__(self,
                 models: Optional[list[Union[gurobipy.Model]]] = None,
                 solver: Optional[str] = "GRB",
                 solver_settings: Optional[SolverSettings] = SolverSettings()) -> None:
        self.models = models
        self.solver = solver
        self.solver_settings = solver_settings
        self.solver_caller = generate_solver_caller(solver, solver_settings)
        self.results: dict[str, list[Output]] = {'simplex': [],
                                                 'barrier': [],
                                                 'barrier_noCrossover': [],
                                                 'cnet': [],
                                                 'tnet': [],
                                                 'perturb_barrier': []}

    def run_barrier(self) -> None:
        for model in self.models:
            self.solver_caller.read_model(model)
            self.solver_caller.run_barrier()
            self.results['barrier'].append(self.solver_caller.return_output())

    def run_simplex(self) -> None:
        for model in self.models:
            self.solver_caller.read_model(model)
            self.solver_caller.run_simplex()
            self.results['simplex'].append(self.solver_caller.return_output())

    def run_mcf_crossover(self) -> None:
        # Todo: makesure flows in mcf has no lower bound other than 0.
        for model in self.models:
            self.solver_caller.read_model(model)
            self.solver_caller.run_barrier_no_crossover()
            self.results['barrier_noCrossover'].append(self.solver_caller.return_output())
            self.results['cnet'].append(
                cnet(
                    self.solver_caller.return_MCF(),
                    self.solver_caller.return_x(),
                    self.solver
                )
            )

    def run_ot_crossover(self) -> None:
        for model in self.models:
            self.solver_caller.read_model(model)
            self.solver_caller.run_barrier_no_crossover()
            self.results['barrier_noCrossover'].append(self.solver_caller.return_output())
            self.results['cnet'].append(
                cnet_ot()
            )
            self.results['tnet'].append(
                tnet_ot()
            )

    def run_lp_crossover(self, model_name: str = '') -> None:
        for model in self.models:
            if model_name != '' and model.ModelName != model_name:
                continue
            self.solver_caller.read_model(model)
            self.results['perturb_barrier'].append(
                run_perturb_algorithm(self.solver_caller.return_StdLP(), self.solver, self.solver_settings)
            )

    def run_lp_barrier(self, model_name: str = '') -> None:
        for model in self.models:
            if model_name != '' and model.ModelName != model_name:
                continue
            self.solver_caller.read_model(model)
            self.solver_caller.run_barrier()
            self.results['barrier'].append((self.solver_caller.return_output()))
