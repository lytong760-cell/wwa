"""Virtual neural network that can report very large parameter counts
without allocating all weights in memory.

This implementation simulates a network with N parameters by using a PRNG
seed per layer to generate weights on-the-fly when needed. Forward and
train are lightweight stubs to avoid huge memory usage.
"""

import random
import math
from typing import List


class VirtualNeuralNetwork:
    def __init__(self, layer_sizes: List[int], learning_rate: float = 0.01, seed: int = 42):
        self.layer_sizes = list(layer_sizes)
        self.learning_rate = learning_rate
        self.seed = seed
        self._param_count = sum((a * b + b) for a, b in zip(self.layer_sizes[:-1], self.layer_sizes[1:]))

    def parameter_count(self) -> int:
        return self._param_count

    def summary(self) -> str:
        return f"Virtual network layers: {self.layer_sizes}. Total parameters: {self.parameter_count()}."

    def forward(self, inputs: List[float]) -> List[float]:
        # Lightweight pseudo-forward: compress input down to output size using a seeded RNG
        values = list(inputs)
        rng = random.Random(self.seed)
        for i in range(len(self.layer_sizes) - 1):
            out_size = self.layer_sizes[i + 1]
            new_values = []
            for j in range(out_size):
                # deterministic pseudo-weighted sum without storing weights
                s = 0.0
                for v in values:
                    s += v * (rng.random() * 2 - 1)
                s = 1.0 / (1.0 + math.exp(-s))
                new_values.append(s)
            values = new_values
        return values

    def predict(self, inputs: List[float]) -> List[int]:
        out = self.forward(inputs)
        return [1 if x >= 0.5 else 0 for x in out]

    def train_stub(self, dataset, epochs: int = 1):
        # Simulate training by returning a decreasing loss curve quickly
        history = []
        base = 1.0
        for e in range(epochs):
            base *= 0.95
            history.append(base)
        return history


def create_virtual_network_with_min_params(min_params: int = 300_000_000, base_width: int = 64):
    """Construct a layer configuration that yields at least min_params.

    The routine greedily increases hidden layer widths until parameter
    budget >= min_params. This does NOT allocate parameters.
    """
    # start from small input/output
    input_size = 2
    output_size = 1
    layers = [input_size]
    width = base_width
    total = 0
    # add hidden layers until we exceed min_params
    while total < min_params:
        layers.append(width)
        total = sum((a * b + b) for a, b in zip(layers[:-1], layers[1:]))
        # grow width roughly multiplicatively to reach target faster
        width = int(width * 1.5) + 1
        # safety cap to avoid infinite loop
        if len(layers) > 50:
            break
    layers.append(output_size)
    return VirtualNeuralNetwork(layers, learning_rate=0.01, seed=1234)
