from qiskit import QuantumCircuit,transpile
from qiskit.circuit.random import random_circuit
from qiskit.converters import circuit_to_dag
from qiskit.dagcircuit import DAGCircuit, DAGOpNode
from qiskit.visualization import dag_drawer
import networkx as nx
import matplotlib.pyplot as plt

class SystemManager :
    def __init__(self):
        return

    def DAG_Convert(self, circuit: QuantumCircuit):
        """
        This function transform all trinary operators into basic gates and return a DAG representation.
        :param circuit:
        :return: qiskit.dagcircuit.DAGCircuit
        """
        basis_gates = ['sx', 'rz', 'cx']
        decomposed_circuit = transpile(circuit, basis_gates=basis_gates) # decompose all operation with more than 2 operands into basic operations
        dag = circuit_to_dag(decomposed_circuit)
        #dag_drawer(dag, filename='dag_original.png')
        for node in list(dag.op_nodes()): # transform all unary operation into edges
            if node.num_qubits == 1:
                dag.remove_op_node(node)

        return dag

    def DAG_to_weighted_graph(self,dag:DAGCircuit):
        G = nx.DiGraph()
        for edge in dag.edges():
            src, dest,_ = edge
            if type(src) == DAGOpNode and type(dest) == DAGOpNode:
                if src.num_qubits == 2 and dest.num_qubits == 2:
                    G.add_node(src._node_id, name=src.name)
                    G.add_node(dest._node_id, name=dest.name)
                    # G.add_node(src.name)
                    # G.add_node(dest.name)
                    if G.has_edge(src._node_id, dest._node_id):
                        G[src._node_id][dest._node_id]['weight'] += 1
                    else:
                        G.add_edge(src._node_id, dest._node_id, weight=1)
        return G

sysman = SystemManager()

test = random_circuit(5, 5, max_operands=2)

dag = sysman.DAG_Convert(test)
dag_drawer(dag,filename='dag.png')
g = sysman.DAG_to_weighted_graph(dag)

# print("Nodes in graph:", g.nodes(data=True))
# print("Edges in graph:", g.edges(data=True))

pos = nx.spring_layout(g)
nx.draw(g, pos, with_labels=False, node_color='lightblue', node_size=2000, font_size=10)

node_labels = nx.get_node_attributes(g, 'name')
nx.draw_networkx_labels(g, pos, labels=node_labels, font_size=12)

edge_labels = nx.get_edge_attributes(g, 'weight')
nx.draw_networkx_edge_labels(g, pos, edge_labels=edge_labels, font_size=10)

plt.savefig("output.png")
plt.show()