import copy
import math
import random

from memory_profiler import profile
from qiskit import QuantumCircuit,transpile
from qiskit.converters import circuit_to_dag
from qiskit.dagcircuit import DAGCircuit, DAGOpNode
import networkx as nx
import matplotlib.pyplot as plt
import gc
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

    def circuit_scheduling(self,graph:nx.Graph,W:dict,P:dict,community:dict):

        """
        view of A:

        {worker_id : {"partitions" : [ids of partition] , 
                      "capacities" : qubits capacity in Integer}}

        P :
        {partition_id : [communities]}
        """
        A = {}
        for worker in W.keys(): # init
            A[worker] = {"partitions": [], "capacities": W[worker]}
        
        for p_i,communities in P.items():
            nodes = self.unfold_partition(communities, community)
            subg = graph.subgraph(nodes)
            p_cap = Qbits(subg)
            w_id = self.find_closest_worker(p_cap,W)
            A[w_id]["partitions"] += [p_i]

        
        A = dict(sorted(A.items(), key=lambda item: item[1]["capacities"], reverse=True)) # from python 3.7 dict can be accessed by sorted result
        for w_id_i in A.keys():
            WP = []
            for w_id_j in A.keys():
                if w_id_i != w_id_j:
                    if A[w_id_j]["capacities"] > A[w_id_i]["capacities"]:
                        WP.append(w_id_j)
            if len(WP) != 0:
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
        
    
    def unfold_partition(self,partition_rst:list,community:dict):
        partition_nodes = []
        for id in partition_rst:
            partition_nodes += community[id]
        return partition_nodes

    def obj(self, graph:nx.Graph,A:dict, input_qbits, community:dict , partition:dict):
        nc = 0
        ru = 0
        sum_qbits = 0
        for worker_info in A.values():
            partition_pack = worker_info["partitions"]
            partition_info = self.unfold_partition(partition_pack,community)
            subg = graph.subgraph(partition_info)
            sum_qbits += Qbits(subg)
        nc = sum_qbits - input_qbits
        diff = 0
        for worker_scheduled in A.values():
            for scheduled_partition in worker_scheduled["partitions"]:
                nodes = self.unfold_partition_for_scheduler(scheduled_partition,partition,community)
                subg = graph.subgraph(nodes)
                diff += Qbits(subg) - input_qbits
        return nc, diff

    def unfold_partition_for_scheduler(self, partition_id, partition:dict, community: dict):
        coms = partition[partition_id]
        nodes = []
        for com in coms:
            nodes += community[com]
        return nodes

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

        for community_id, nodes in communities.items():
            for node in nodes:
                for neighbor, edge_data in graph[node].items():
                    if neighbor in nodes:
                        continue
                    for community_id_2, nodes_2 in communities.items():
                        if neighbor in nodes_2:
                            if merged_graph.has_edge(community_id, neighbor):
                                merged_graph[community_id][community_id_2]['weight'] += edge_data.get('weight', 1)
                            else:
                                merged_graph.add_edge(community_id, community_id_2, weight=edge_data.get('weight', 1))
        nx.draw(merged_graph,with_labels=True)
        plt.savefig("mergedCommunity.png")
        plt.show()
        return merged_graph

    def fitCut_Optimization(self, graph:nx.Graph, community: dict, W:dict, W_max_qbits, input_qbits):
        #initialization
        merged_graph = self.merge_communities_in_graph(graph,community)
        P = {}
        neighbour = {} # neighbour is a dictionary that stores the id of community and its neighbour partition
        for id in community.keys():
            P[id] = [id]
            neighbour[id] = list(merged_graph.neighbors(id)) # at the beginning the neighbout of each community is just other communities
        
        improvement  = True
        num_of_partitions = len(community.keys())
        while improvement:
            improvement = False
            #TODO : Here I would interprete the meaning of the pseudo code is just to iterate through all community
            # And the using of P is just to quickly refer to its belonging partition.
            # Here based on the pseudo code we can add a list containing all the iterated community to avoid double iteration
            # or we can just iterating a list containing all the communities and try to locate its partition
            for i in range(num_of_partitions): # use index instead, avoiding changing loop condition
                iterated_community = []
                p_id, p_value = list(P.items())[i]
                bo_1 = float("inf")
                bo_2 = float("inf")
                for community_id in p_value: # for each community in a partition
                    if community_id in iterated_community:
                        continue
                    for neighbour_partitions in neighbour[community_id]:
                        iterated_community.append(community_id)
                        gc.collect()
                        #print("all neighbour: ",neighbour)# for each neighbouring partition
                        #print("neighbour: " ,neighbour[community_id])
                        #print("neighbour_partitions: " ,neighbour_partitions)
                        #print("P: ", P)
                        #print("community: ",community)
                        #print("community_id: ",community_id)
                        #print("copy")
                        P_updated = copy.deepcopy(P)
                        P_updated[p_id].remove(community_id)
                        P_updated[neighbour_partitions].append(community_id) # try assign a community from neighbour partition to current partition
                        # P_updated = P.copy()
                        # P_updated[p_id] = P[p_id][:]
                        # P_updated[p_id].remove(community_id)
                        # P_updated[neighbour_partitions] = P[neighbour_partitions][:]
                        # P_updated[neighbour_partitions].append(community_id)
                        #print(P_updated)
                        neighbour = self.neighbourUpdate(neighbour_partitions,community_id,neighbour)
                        #print(self.maxPartitionQubits(graph,P_updated,community), W_max_qbits)
                        if self.maxPartitionQubits(graph,P_updated,community) < W_max_qbits:
                            A = self.circuit_scheduling(graph,W,P_updated,community)
                            nc,ru = self.obj(graph,A,input_qbits,community,P_updated)
                            #print("nc,ru:", nc, ru)
                            if nc< bo_1:
                                P = P_updated
                                bo_1 = nc
                                bo_2 = ru
                                improvement = True
                            elif nc == bo_1 and ru < bo_2:
                                P = P_updated
                                bo_2 = ru
                                improvement = True
                        if improvement: # we have reassigned current community to another partition, no need to iterate over another neighbours
                            break
                        #print(improvement)

        A = self.circuit_scheduling(graph,W,P,community)
        print("final partition:" , P)
        print("finished optimization")
        return P,A

    def neighbourUpdate(self,p_id,community_id,neighbour):
        neighbour[p_id] += neighbour[community_id]
        neighbour[p_id] = list(set(neighbour[p_id]))
        neighbour[community_id].remove(p_id)
        return neighbour

    def maxPartitionQubits(self,graph:nx.Graph,partition,communities):
        qbits = []
        for parts in partition.values():
            node_ids = []
            for partition_id in parts:
                node_ids+= communities[partition_id]
            subg = graph.subgraph(node_ids)
            qbits.append(Qbits(subg))

        return max(qbits)



            



