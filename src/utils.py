import networkx as nx

def Qbits(circuit:nx.Graph):
    weight = sum(data['weight'] for _, _, data in circuit.edges(data=True))
    qubits = 2 * circuit.number_of_nodes() - weight
    return qubits