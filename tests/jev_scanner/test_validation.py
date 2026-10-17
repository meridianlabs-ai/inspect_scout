"""prob_threshold validation predicate."""

import pytest
from inspect_scout import Result, prob_threshold


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "p,target,threshold,valid",
    [
        (0.7, True, 0.5, True),
        (0.7, True, 0.8, False),
        (0.3, False, 0.5, True),
        (0.6, False, 0.5, False),
    ],
)
async def test_prob_threshold(
    p: float, target: bool, threshold: float, valid: bool
) -> None:
    predicate = prob_threshold(threshold)
    assert await predicate(Result(value=p >= 0.5, metadata={"p": p}), target) is valid


@pytest.mark.asyncio
async def test_prob_threshold_requires_probability() -> None:
    with pytest.raises(TypeError, match="metadata"):
        await prob_threshold()(Result(value=True), True)
