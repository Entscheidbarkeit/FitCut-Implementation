import networkx as nx
from matplotlib import pyplot as plt
from qiskit.circuit.random import random_circuit
from qiskit.visualization import dag_drawer

from src.CommunityDetection.detector import CommunityDetector
from src.SysMan.SysMan import SystemManager

if __name__ == "__main__":

    test = random_circuit(7, 8, max_operands=2, seed=123455)

    sysman = SystemManager()
    dag = sysman.DAG_Convert(test)
    dag_drawer(dag, filename='dag.png')
    g = sysman.DAG_to_weighted_graph(dag)

    relabeled_g, mapping = sysman.relabel_graph_nodes(g)
    sysman.graph_text_format(relabeled_g)

    # print("Nodes in graph:", g.nodes(data=True))
    # print("Edges in graph:", g.edges(data=True))
    plt.figure(figsize=(20, 20))
    pos = nx.spring_layout(g)
    nx.draw(g, pos, with_labels=False, node_color='lightblue', node_size=600)

    node_labels = nx.get_node_attributes(g, 'name')
    nx.draw_networkx_labels(g, pos, labels=node_labels, font_size=12)

    edge_labels = nx.get_edge_attributes(g, 'weight')
    nx.draw_networkx_edge_labels(g, pos, edge_labels=edge_labels, font_size=10)

    plt.savefig("output.png")

    cd = CommunityDetector(relabeled_g)
    cd.process_graph("../src/text_graph.txt")
    cd.read_meta()
    com = cd.community_reconstruction()
    cd.draw_colored_community(com)
