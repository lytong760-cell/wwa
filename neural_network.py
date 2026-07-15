"""Large pure-Python neural network implementation.

This module provides a dense neural network with multiple hidden layers and
supports building a model with many parameters without external dependencies.
"""

import math
import random


def sigmoid(x):
    return 1.0 / (1.0 + math.exp(-x))


def dsigmoid(output):
    return output * (1.0 - output)


class DenseLayer:
    def __init__(self, input_size, output_size):
        self.input_size = input_size
        self.output_size = output_size
        self.weights = [[random.uniform(-1, 1) for _ in range(input_size)] for _ in range(output_size)]
        self.bias = [random.uniform(-1, 1) for _ in range(output_size)]
        self.last_input = None
        self.last_output = None

    def forward(self, inputs):
        self.last_input = inputs
        outputs = []
        for neuron_weights, neuron_bias in zip(self.weights, self.bias):
            total = neuron_bias
            for weight, value in zip(neuron_weights, inputs):
                total += weight * value
            outputs.append(sigmoid(total))
        self.last_output = outputs
        return outputs

    def backward(self, output_gradients, learning_rate):
        input_gradients = [0.0] * self.input_size
        for j in range(self.output_size):
            delta = output_gradients[j] * dsigmoid(self.last_output[j])
            for i in range(self.input_size):
                input_gradients[i] += delta * self.weights[j][i]
                self.weights[j][i] += learning_rate * delta * self.last_input[i]
            self.bias[j] += learning_rate * delta
        return input_gradients

    def parameter_count(self):
        return self.input_size * self.output_size + self.output_size


class NeuralNetwork:
    def __init__(self, layer_sizes, learning_rate=0.05):
        if len(layer_sizes) < 2:
            raise ValueError("layer_sizes must have at least input and output sizes")
        self.layers = [DenseLayer(layer_sizes[i], layer_sizes[i + 1]) for i in range(len(layer_sizes) - 1)]
        self.learning_rate = learning_rate

    def forward(self, inputs):
        values = inputs
        for layer in self.layers:
            values = layer.forward(values)
        return values

    def predict(self, inputs):
        outputs = self.forward(inputs)
        return [1 if x >= 0.5 else 0 for x in outputs]

    def train(self, inputs, targets):
        outputs = self.forward(inputs)
        errors = [targets[i] - outputs[i] for i in range(len(targets))]
        gradients = [errors[i] for i in range(len(errors))]
        for layer in reversed(self.layers):
            gradients = layer.backward(gradients, self.learning_rate)
        loss = sum(error * error for error in errors) / len(errors)
        return loss

    def parameter_count(self):
        return sum(layer.parameter_count() for layer in self.layers)

    def summary(self):
        sizes = [self.layers[0].input_size] + [layer.output_size for layer in self.layers]
        return f"Neural network layers: {sizes}. Total parameters: {self.parameter_count()}."


def create_large_network():
    """Create a large network with many parameters for demonstration."""
    return NeuralNetwork([2, 128, 64, 32, 1], learning_rate=0.1)


def create_huge_network():
    """Create a much larger network with a high parameter count for demo."""
    return NeuralNetwork([2, 512, 256, 128, 64, 32, 16, 1], learning_rate=0.05)


def create_ultra_network():
    """Create an ultra-large network with as many parameters as practical in pure Python."""
    return NeuralNetwork([2, 1024, 512, 256, 128, 64, 32, 1], learning_rate=0.05)


def train_xor_model(network, epochs=1000):
    dataset = [
        ([0.0, 0.0], [0.0]),
        ([0.0, 1.0], [1.0]),
        ([1.0, 0.0], [1.0]),
        ([1.0, 1.0], [0.0]),
    ]
    history = []
    for epoch in range(epochs):
        total_loss = 0.0
        for inputs, targets in dataset:
            total_loss += network.train(inputs, targets)
        history.append(total_loss / len(dataset))
    return history


def sample_prediction(network):
    dataset = [
        ([0.0, 0.0], [0.0]),
        ([0.0, 1.0], [1.0]),
        ([1.0, 0.0], [1.0]),
        ([1.0, 1.0], [0.0]),
    ]
    return [(inputs, network.predict(inputs)) for inputs, _ in dataset]
