"""Implementations for classes in q_learning_v2.py."""

from typing import Dict, Iterable, Tuple

import numpy
from keras import layers
from keras import models

from lib import q_learning_v2


class KerasModelQFunction(q_learning_v2.QFunction):
    """A Q-Function implementation using a model built in Keras."""

    def __init__(
        self,
        env: q_learning_v2.Environment,
        num_nodes_in_layers: Iterable[int],
        learning_rate: float = None,
        discount_factor: float = None,
    ):
        """Constructor.
        
        Args:
            state_array_size: the size of the state arrays.
            action_space: the action space.
            num_nodes_in_layers: a list of how many nodes are used in each
                layer, starting from the input layter.
        """
        super().__init__(
            learning_rate=learning_rate,
            discount_factor=discount_factor)
            
        self._env = env
        self._state_array_size = env.GetStateArraySize()
        self._action_space_size = len(env.GetActionSpace())
        self._input_size = self._state_array_size + self._action_space_size
        
        self._model = _BuildClassifierModel(
            self._env.GetStateArraySize(),
            len(self._env.GetActionSpace()),
            num_nodes_in_layers)
        
        self._debug_verbosity = 0
        
    def SetDebugVerbosity(self, debug_verbosity: int) -> None:
        """Sets the debug verbosity, which controls the amount of output."""
        self._debug_verbosity = debug_verbosity

    # @Override
    def GetValue(
        self,
        state: q_learning_v2.State,
        action: q_learning_v2.Action,
    ) -> float:
        value = self._model.predict(self._GetStateActionArray(state, action))
        if self._debug_verbosity >= 5:
            print('GET: (%s, %s) -> %s' % (state, action, value))
        return value
        
    # @Override
    def _SetValue(
        self,
        state: q_learning_v2.State,
        action: q_learning_v2.Action,
        new_value: float,
    ) -> None:
        if self._debug_verbosity >= 5:
            print('SET: (%s, %s) <- %s' % (state, action, new_value))
        return self._model.fit(
            self._GetStateActionArray(state, action), new_value, verbose=0)
            
    def _GetStateActionArray(
        self,
        state: q_learning_v2.State,
        action: q_learning_v2.Action,
    ) -> numpy.ndarray:
        """Creates a (state, action) array."""
        input_array = numpy.zeros((1, self._input_size))
        input_array[0, :self._state_array_size] = state
        # Use hot-spot for action.
        input_array[0, self._state_array_size + action] = 1.0
        return input_array
        
    # @Shadow
    def UpdateWithTransition(
        self,
        state_t: q_learning_v2.State,
        action_t: q_learning_v2.Action,
        reward_t: q_learning_v2.Reward,
        state_t_plus_1: q_learning_v2.State,
    ) -> None:
        """Updates values by a transition.
        
        Args:
            state_t: the state at t.
            action_t: the action to perform at t.
            reward_t: the direct reward as the result of (s_t, a_t).
            state_t_plus_1: the state to land at after action_t.
        """
        super().UpdateWithTransition(
            state_t, action_t, reward_t, state_t_plus_1, self._env.GetActionSpace())
    

def _BuildClassifierModel(
    state_array_size: int,
    action_space_size: int,
    num_nodes_in_layers:Iterable[int],
) -> models.Model:
    """Builds a model with the given info."""
    input_size = state_array_size + action_space_size
    model = models.Sequential()
    model.add(
        layers.Dense(input_size, activation='relu', input_dim=input_size))
    for num_nodes in num_nodes_in_layers:
        model.add(layers.Dense(num_nodes, activation='relu'))
    model.add(layers.Dense(1))
    
    model.compile(optimizer='sgd', loss='mse')
    
    return model    
    
    
class MaxValuePolicy(q_learning_v2.Policy):
    """A policy that returns the action that yields the max value."""
    
    # @Override
    def Decide(
        self,
        q_function: q_learning_v2.QFunction,
        current_state: q_learning_v2.State,
        action_space: q_learning_v2.ActionSpace,
    ) -> q_learning_v2.Action:
        max_value = -numpy.inf
        max_value_action = None
        for action in action_space:
            try_value = q_function.GetValue(current_state, action)
            if try_value > max_value:
                max_value = try_value
                max_value_action = action
        return max_value_action


class RandomActionPolicy(q_learning_v2.Policy):
    """A policy that returns a random action."""
    
    # @Override
    def Decide(
        self,
        q_function: q_learning_v2.QFunction,
        current_state: q_learning_v2.State,
        action_space: q_learning_v2.ActionSpace,
    ) -> q_learning_v2.Action:
        return numpy.random.choice(action_space)


class MaxValueWithRandomnessPolicy(q_learning_v2.Policy):
    """A policy that returns the action that yields the max value."""
    
    def __init__(self, certainty: float = 0.9):
        self._certainty = certainty
        
        self.debug_verbosity = 0
    
    # @Override
    def Decide(
        self,
        q_function: q_learning_v2.QFunction,
        current_state: q_learning_v2.State,
        action_space: q_learning_v2.ActionSpace,
    ) -> q_learning_v2.Action:
        max_value = -numpy.inf
        max_value_action = None
        for action in action_space:
            try_value = q_function.GetValue(current_state, action)
            if try_value > max_value:
                max_value = try_value
                max_value_action = action

        if numpy.random.random() < self._certainty:
            return max_value_action
        else:
            if self.debug_verbosity >= 2:
                print('<use random choice>')
            return numpy.random.choice(action_space)