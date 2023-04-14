from typing import Optional

import gurobipy
import numpy as np

from smart_crossover import get_project_root
from smart_crossover.formats import OptTransport, MinCostFlow
from smart_crossover.network_methods.net_manager import OTManager, MCFManager, NetworkManager
from smart_crossover.network_methods.tree_BI import tree_basis_identify
from smart_crossover.output import Output
from smart_crossover.parameters import COLUMN_GENERATION_RATIO
from smart_crossover.solver_caller.gurobi import GrbCaller
from smart_crossover.timer import Timer


def network_crossover(
        x: np.ndarray[np.float_],
        ot: Optional[OptTransport] = None,
        mcf: Optional[MinCostFlow] = None,
        method: str = "tnet",
        solver: str = "GRB",
    ) -> Output:
    """
    Solve the network problem (MCF/OT) using TNET, CNET_OT, or CNET_MCF algorithms.

    Args:
        ot: the optimal transport problem (for TNET and CNET_OT).
        mcf: the minimum cost flow problem (for CNET_MCF).
        x: an interior-point / inaccurate solution of the network problem to warm-start the basis identification.
        method: the algorithm to use ('tnet', 'cnet_ot', or 'cnet_mcf').
        solver: the solver to use.

    Returns:
        the output of the selected algorithm.

    """

    # Set the timer.
    timer = Timer()
    timer.start_timer()

    if method == "tnet" or method == "cnet_ot":
        manager = OTManager(ot)
    elif method == "cnet_mcf":
        manager = MCFManager(mcf)
    else:
        raise ValueError("Invalid method specified. Choose from 'tnet', 'cnet_ot', or 'cnet_mcf'.")

    # Get sorted flows from the interior-point solution x.
    queue, flow_indicators = manager.get_sorted_flows(x)

    if method == "tnet":
        manager.set_basis(tree_basis_identify(manager, flow_indicators))
    else:  # method in ["cnet_ot", "cnet_mcf"]
        if method == "cnet_ot":
            manager.extend_by_bigM(manager.n * np.max(ot.M))
        elif method == "cnet_mcf":
            manager.rescale_cost(np.max(np.abs(mcf.c)))
            manager.fix_variables(ind_fix_to_up=np.where(x >= mcf.u / 2)[0], ind_fix_to_low=np.where(x < mcf.u / 2)[0])
            manager.extend_by_bigM(manager.n * np.max(mcf.u))
        manager.update_subproblem()
        manager.set_initial_basis()

    timer.end_timer()
    cg_output = column_generation(manager, queue, solver)

    return Output(x=cg_output.x, obj_val=cg_output.obj_val, runtime=timer.total_duration + cg_output.runtime,
                  basis=cg_output.basis)


def column_generation(net_manager: NetworkManager,
                      queue: np.ndarray[np.int64],
                      solver: str) -> Output:

    # Initialize the column generation.
    timer = Timer()
    timer.start_timer()
    left_pointer = 0
    num_vars_in_next_subproblem = int(1.2 * net_manager.m)
    is_not_optimal = True
    x = None
    obj_val = None
    iter_count = 0

    while is_not_optimal:

        if left_pointer >= len(queue):
            print(' ##### Column generation fails! #####')
            break
        right_pointer = min(num_vars_in_next_subproblem, len(queue))
        net_manager.add_free_variables(queue[left_pointer:right_pointer])
        net_manager.update_subproblem()

        # Solve the sub problem.
        timer.end_timer()
        sub_output = net_manager.solve_subproblem(solver)
        obj_val = net_manager.recover_obj_val(sub_output.obj_val)
        timer.accumulate_time(sub_output.runtime)
        timer.start_timer()

        # Update the basis.
        net_manager.set_basis(net_manager.recover_basis_from_sub_basis(sub_output.basis))

        # Recover the solution.
        x = net_manager.recover_x_from_sub_x(sub_output.x)

        # Check stop criterion, and update num_vars_in_next_subproblem.
        if net_manager.check_optimality_condition(x, sub_output.y):
            is_not_optimal = False

        num_vars_in_next_subproblem = int(COLUMN_GENERATION_RATIO * num_vars_in_next_subproblem)
        left_pointer = right_pointer
        iter_count += sub_output.iter_count

    timer.end_timer()
    return Output(x=x, obj_val=obj_val, runtime=timer.total_duration, iter_count=iter_count, basis=net_manager.basis)


# Debug
goto_mps_path = get_project_root() / "data/goto"
model = gurobipy.read("/Users/jian/Documents/2023 Spring/smart-crossover/data/goto/netgen_8_14a.mps")
gur_runner = GrbCaller()
gur_runner.read_model(model)
x = np.load("/Users/jian/Documents/2023 Spring/smart-crossover/data/goto/x_netgen.npy")
mcf = gur_runner.return_MCF()
network_crossover(x, mcf=mcf, method="cnet_mcf", solver="GRB")
