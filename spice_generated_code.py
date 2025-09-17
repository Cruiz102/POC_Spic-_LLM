import PySpice.Logging.Logging as Logging
logger = Logging.setup_logging()

from PySpice.Spice.Netlist import Circuit
from PySpice.Unit import *

circuit = Circuit('Parallel RC branches')

circuit.V('input', 'n1', circuit.gnd, 1@u_V)
circuit.R(1, 'n1', circuit.gnd, 1@u_Ohm)
circuit.R(2, 'n1', circuit.gnd, 2@u_Ohm)
circuit.R(3, 'n1', circuit.gnd, 3@u_Ohm)
circuit.R(4, 'n1', circuit.gnd, 4@u_Ohm)
circuit.C(1, 'n1', circuit.gnd, 3@u_uF)

simulator = circuit.simulator(temperature=25, nominal_temperature=25)
analysis = simulator.operating_point()

for node in analysis.nodes.values():
    print('Node {}: {:4.1f} V'.format(str(node), float(node)))