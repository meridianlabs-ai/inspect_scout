import pickle

from inspect_scout._concurrency._mp_common import DillCallable

_rebuilds = 0


class _CostlyState:
    """Counts its rebuilds on unpickle, like a compiled regex that recompiles."""

    def __reduce__(self) -> tuple[object, tuple[()]]:
        return (_rebuild, ())


def _rebuild() -> _CostlyState:
    global _rebuilds
    _rebuilds += 1
    return _CostlyState()


def test_a_worker_unpickles_the_function_once() -> None:
    state = _CostlyState()

    def scan(n: int) -> int:
        assert isinstance(state, _CostlyState)
        return n + 1

    # The spawn context hands each worker the callable pickled.
    in_worker = pickle.loads(pickle.dumps(DillCallable(scan)))
    before = _rebuilds

    assert [in_worker(n) for n in range(3)] == [1, 2, 3]
    assert _rebuilds - before == 1
