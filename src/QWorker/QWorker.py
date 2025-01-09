import random


class QuantemWorker:
    """
    we define the data structure of Quantum Worker as dictionary with key as id and value as max qubits
    """
    def __init__(self):
        pass

    @staticmethod
    def random_generate(num, max_Capacity, seed = 12345):
        random.seed(seed)
        W = {}
        for i in range(num):
            W[i] = random.randint(0,max_Capacity)

        return W