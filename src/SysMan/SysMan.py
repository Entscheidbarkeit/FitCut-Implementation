from qiskit import QuantumCircuit,transpile
from qiskit.converters import circuit_to_dag
from qiskit.dagcircuit import DAGCircuit, DAGOpNode
import networkx as nx



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
        G = nx.Graph()
        for edge in dag.edges(): #TODO: we need to store the degree of vertices too
            src, dest,_ = edge
            if type(src) == DAGOpNode and type(dest) == DAGOpNode:
                if src.num_qubits == 2 and dest.num_qubits == 2:
                    G.add_node(src._node_id, name=src.name)
                    G.add_node(dest._node_id, name=dest.name)
                    if G.has_edge(src._node_id, dest._node_id):
                        G[src._node_id][dest._node_id]['weight'] += 1
                    else:
                        G.add_edge(src._node_id, dest._node_id, weight=1)
        return G

    def relabel_graph_nodes(self, graph: nx.Graph):
        mapping = {old: new for new, old in enumerate(graph.nodes(), start=0)}
        new_graph = nx.relabel_nodes(graph, mapping, copy=True)
        return new_graph, mapping

    def graph_text_format(self, graph:nx.Graph):
        file = open("text_graph.txt", "w")
        for edge in graph.edges(data=True):
            src, dest, data = edge
            file.write(f"{src} {dest} {data['weight']} \n")
        file.close()

