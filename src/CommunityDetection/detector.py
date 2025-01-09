import subprocess
import networkx as nx
import re
import pandas as pd
from matplotlib import pyplot as plt
from src.utils import Qbits

class CommunityDetector:
    def __init__(self, graph:nx.Graph, QWorker_max_capacity:int=100):
        self.level_data = {}
        self.number_of_levels = 0
        self.graph = graph
        self.QWorker_max_capacity = QWorker_max_capacity

    def process_graph(self,graph_file):
        rst = subprocess.run(
            ["CommunityDetectionExecutable/convert", "-i", graph_file ,"-o","graph.bin", "-w", "graph.weights"]
        )
        with open("graph.tree", "w") as f:
            rst = subprocess.run(
                ["CommunityDetectionExecutable/community", "graph.bin", "-l", "-1", "-w", "graph.weights"]
            , stdout = f
            )
        f.close()

    def read_meta(self):
        rst = subprocess.run(['CommunityDetectionExecutable/hierarchy', 'graph.tree'], capture_output=True, text=True)
        output = rst.stdout
        self.number_of_levels = int(re.search(r"Number of levels: (\d+)", output).group(1))
        levels = re.findall(r"level (\d+): (\d+) nodes", output)
        self.level_data = {int(level): int(nodes) for level, nodes in levels}

    def community_reconstruction(self):
        """
        The idea here is not to modify the original C++ code, for that it might create bugs.
        The output of C++ project means:
            the first column, the id of node,
            the second column, the id of community, which will be taken as new node id in the next level.
            next Level starts when the id of nodes turns 0.

        this method start with an initial communities, where each node is itself a community
        then the community agglomerate to generation new communities of next level.
        After each level of new communities of generation, the constraints will be checked.

        If the constraint is violated, the new communities will be deprecated and the old one will be returned.
        If the iteration stopped with no violation, the last level of communities will be returned.
        :return: the last valid communities, stored in dictionaries ,with key as index of communities and value the array of belonging nodes
        """
        tree = pd.read_csv("graph.tree", sep =" ", header=None).to_numpy().astype("int")

        communities = {}
        for node in self.graph.nodes: #init
            communities[f"{node}"] = [int(node)]
        hist = 0
        for level in range(self.number_of_levels): # level from 0 to max
            new_communities = {}
            for line in range(hist,hist+self.level_data[level]): # agglomerate communities
                try:
                    original = new_communities[f"{tree[line][1]}"]
                    new_communities[f"{tree[line][1]}"] = original+communities[f"{tree[line][0]}"]
                except KeyError:
                    new_communities[f"{tree[line][1]}"] = communities[f"{tree[line][0]}"]
            hist += self.level_data[level]

            for community in new_communities.values(): # constraint
                subgraph = self.graph.subgraph(community)

                # weight_sub = sum(data['weight'] for _, _, data in subgraph.edges(data=True))
                # qubits = 2 * len(community) - weight_sub
                qubits = Qbits(subgraph)
                if qubits > self.QWorker_max_capacity / 2:
                    return communities

            communities = new_communities

        return communities

    def draw_colored_community(self, communities):
        community_colors = {}
        for community_id, nodes in enumerate(communities.values()):
            for node in nodes:
                community_colors[node] = community_id

        node_colors = [community_colors[node] for node in self.graph.nodes]

        pos = nx.spring_layout(self.graph)
        plt.figure(figsize=(10, 8))
        nx.draw(
            self.graph,
            pos,
            with_labels=True,
            node_color=node_colors,
            cmap=plt.cm.get_cmap('tab20'),
            node_size=500,
            font_size=10
        )
        plt.title("Community Graph")
        plt.show()



