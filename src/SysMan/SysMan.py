import copy
import math
import random
from qiskit import QuantumCircuit,transpile
from qiskit.converters import circuit_to_dag
from qiskit.dagcircuit import DAGCircuit, DAGOpNode
import networkx as nx

from src.utils import Qbits



class SystemManager :
    """
    community: a dictionary contains the key as community id and value the belonging node ids
    partition: a dictionary contains the key as partition, which might have multiple communities, and value as the qbits capacity
    """


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
    
    def partition_construct(self, graph:nx.Graph,community:dict):
        """
        merge the partition based on community and calculate the qbits of each partition
        """
        P = {}
        for ids,com in community.items():
            subgraph = graph.subgraph(com)
            P[ids] = Qbits(subgraph)
        return P
    
    def find_closest_worker(self,p_cap, W: dict):
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

    def circuit_scheduling(self,W:dict,P:dict):

        """
        view of A:

        {worker_id : {"partitions" : [ids of partition] , 
                      "capacities" : qubits capacity in Integer}}
        """
        A = {}
        for worker in W.keys(): # init
            A[worker] = {"partitions": [], "capacities": W[worker]}
        
        for p_i,p_cap in P.items():
            w_id = self.find_closest_worker(p_cap,W)
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
        
    
    def unfold_partition(partition_rst:list,community:dict):
        partition_nodes = []
        for id in partition_rst:
            partition_nodes += community[id]
        return partition_nodes

    def obj(self, graph:nx.Graph,A:dict, input_qbits, community:dict):
        nc = 0
        ru = 0
        sum_qbits = 0
        for worker_info in A.values():
            partition_pack = worker_info["partition"]
            partition_info = self.unfold_partition(partition_pack,community)
            subg = graph.subgraph(partition_info)
            sum_qbits += Qbits(subg)
        nc = sum_qbits - input_qbits
        diff = 0
        for worker_scheduled in A.values():
            pass
    
    def merge_communities_in_graph(self, graph:nx.Graph, communities):
        """
        merge the communities as one node based on given graph and return the merged graph.
        the id of communities will be the id of merged node
        weight of the merged edge will be updated

        community: dict
            {community_id : [belonging node_id]}

        return: nx.Graph
        """
        merged_graph = nx.Graph()

        for community_id, nodes in communities.items():
            merged_graph.add_node(community_id)
            
            for node in nodes:
                for neighbor, edge_data in graph[node].items():
                    if neighbor in nodes:
                        continue
                    if neighbor not in communities:
                        if merged_graph.has_edge(community_id, neighbor):
                            merged_graph[community_id][neighbor]['weight'] += edge_data.get('weight', 1)
                        else:
                            merged_graph.add_edge(community_id, neighbor, weight=edge_data.get('weight', 1))

        return merged_graph

    def fitCut_Optimization(self, graph:nx.Graph, community: dict, W:dict, W_max_qbits, input_qbits):
        #initialization
        merged_graph = self.merge_communities_in_graph(graph,community)
        P = {}
        neighbour = {} # neighbour is a dictionary that stores the id of community and its neighbour partition
        for id in community.keys():
            P[id] = id
            neighbour[id] = list(merged_graph.neighbors(id)) # at the beginning the neighbout of each community is just other communities
        
        improvement  = True

        while improvement:
            improvement = False
            for p_id,p_value in P.items():
                bo_1 = float("inf")
                bo_2 = float("inf")
                for community_id in p_value: # for each community in a partition
                    for neighbour_partitions in neighbour[community_id]: # for each neighbouring partition
                        P_updated = copy.deepcopy(P)
                        P_updated[neighbour_partitions].append(community_id)
                        P_updated[p_id].remove(community_id)
                        neighbour_updated = self.neighbourUpdate(neighbour) #TODO
                        if self.maxPartitionQubits() < W_max_qbits: #TODO
                            A = self.circuit_scheduling(W,P_updated)
                            nc,ru = self.obj(graph,A,input_qbits,community)
                            if nc< bo_1:
                                P = P_updated # think of a logic that wont interupte the loop
                                bo_1 = nc
                                bo_2 = ru
                            elif nc == bo_1 and ru < bo_2:
                                P = P_updated
                                bo_2 = ru
                                improvement = True
        A = self.circuit_scheduling(W,P)
        return P,A

            



