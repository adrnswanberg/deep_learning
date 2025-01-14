import numpy

from deep_learning.engine import q_base
from qpylib import t
from qpylib.data_structure import sum_tree


# Doesn't seem to work (tried with DDQN). Keep in experimental for now.
class PrioritizedExperienceReplayRunner(q_base.Runner):
  """A runner that implements prioritized experience replay."""

  def __init__(
      self,
      experience_capacity: int,
      experience_sample_batch_size: int,
      train_every_n_steps: int = 1,
  ):
    super().__init__()
    self._experience_capacity = experience_capacity
    self._experience_sample_batch_size = experience_sample_batch_size
    self._train_every_n_steps = train_every_n_steps

    self._experience = _PrioritizedExperience(
      capacity=self._experience_capacity)

  # @Override
  def _protected_ProcessTransition(
      self,
      qfunc: q_base.QFunction,
      transition: q_base.Transition,
      step_idx: int,
  ) -> None:
    states, actions, action_values = qfunc.UpdateValues([transition])
    err = numpy.sum(numpy.abs(
      qfunc.GetActionValues(qfunc.GetValues(states), actions) - action_values))
    self._experience.AddTransition(transition, float(err))

    if step_idx % self._train_every_n_steps == 0:
      qfunc.UpdateValues(
        self._experience.Sample(self._experience_sample_batch_size))

  def SampleFromHistory(self, size: int) -> t.Iterable[q_base.Transition]:
    """Samples a set of transitions from experience history."""
    return self._experience.Sample(size)


class _PrioritizedExperience:
  """Fixed size experience with priorities.

  Ref:
    https://jaromiru.com/2016/11/07/lets-make-a-dqn-double-learning-and
    -prioritized-experience-replay/
  """

  def __init__(
      self,
      capacity: int,
      epsilon: float = 0.01,
      alpha: float = 0.6,
  ):
    """Constructor.

    Args:
        capacity: how many past events to save. If capacity is full,
            old events are discarded as new events are recorded.
        epsilon: p = (err + epsilon)^alpha
        alpha: p = (err + epsilon)^alpha
    """
    self._capacity = capacity
    self._epsilon = epsilon
    self._alpha = alpha

    # Events inserted later are placed at tail.
    self._history = sum_tree.SumTree(capacity=self._capacity)

  def _CalculatePriority(self, error: float):
    # p = (err + epsilon)^alpha
    return numpy.power(numpy.abs(error) + self._epsilon, self._alpha)

  def AddTransition(
      self,
      transition: q_base.Transition,
      error: float,
  ) -> None:
    """Adds an event to history."""
    p = self._CalculatePriority(error)
    self._history.add(p, transition)

  def Sample(self, size: int) -> t.Iterable[q_base.Transition]:
    """Samples an event from the history."""
    # Gets a random number between 0 and total sum, then get the transition
    # corresponding to it.
    for s in numpy.random.uniform(0, self._history.total(), size=size):
      _, tran = self._history.get(s)
      yield tran
