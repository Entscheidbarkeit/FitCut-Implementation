import math
import random
from qiskit import QuantumCircuit,transpile
from qiskit.converters import circuit_to_dag
from qiskit.dagcircuit import DAGCircuit, DAGOpNode
import networkx as nx

from src.utils import Qbits



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
    
    def partition_construct(graph:nx.Graph,community:dict):
        P = {}
        for ids,com in community.items():
            subgraph = graph.subgraph(com)
            P[ids] = Qbits(subgraph)
        return P
    
    def circuit_scheduling(W:dict,P:dict):

        """
        view of A:

        {worker_id : {"partitions" : [ids of partition] , 
                      "capacities" : qubits capacity in Integer}}
        """
        A = {}
        for worker in W.keys(): # init
            A[worker] = {"partitions": [], "capacities": W[worker]}
        
        for p_i,p_cap in P.items():
            w_id = find_closest_worker(p_cap,W)
            A[w_id]["partitions"] += [p_i]
        
        A = dict(sorted(A.items(), key=lambda item: item[1]["capacities"], reverse=True)) # from python 3.7 dict can be accessed by sorted result
        for w_id_i in A.keys():
            WP = []
            for w_id_j in A.keys():
                if w_id_i != w_id_j:
                    if A[w_id_j]["capacities"] > A[w_id_i]["capacities"]:
                        WP.append(w_id_j)
            total_task = sum(len(A[w_id]["partitions"]) for w_id in WP)
            Max = math.ceil(total_task/len(WP))
            Min = Max -1
            WP = sorted(WP, key = lambda w_id: W[w_id])
            for w_id in WP:
                while len(A[w_id_i]["partitions"]) > Max and len(A[w_id]["partitions"])< Min:
                    p_to_remove = random.choice(A[w_id_i]["partitions"])
                    A[w_id_i]["partitions"].remove(p_to_remove)
                    A[w_id]["partitions"].append(p_to_remove)
                while len(A[w_id_i]["partitions"]) > Max and len(A[w_id]["partitions"])< Max:
                    p_to_remove = random.choice(A[w_id_i]["partitions"])
                    A[w_id_i]["partitions"].remove(p_to_remove)
                    A[w_id]["partitions"].append(p_to_remove)
        
        return A
        
    
def find_closest_worker(p_cap, W: dict):
    """
    Finds the worker with the closest qubit capacity to the given p_cap.

    Args:
        p_cap (int): The target qubit capacity to compare against.
        W (dict): A dictionary where keys are worker names (or IDs)
                  and values are their respective qubit capacities.

    Returns:
        The key of the worker with the closest qubit capacity.
    """
    
    closest_worker = None
    closest_difference = float('inf')

    for worker, capacity in W.items():
        difference = abs(capacity - p_cap)
        if difference < closest_difference:
            closest_difference = difference
            closest_worker = worker

    return closest_worker


