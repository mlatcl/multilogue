from multilogue.multiverse import (
    enumerate_configurations,
    run_multiverse,
    variance_decomposition,
)


def test_enumerate_and_run():
    configs = enumerate_configurations({"k": [2, 3], "threshold": [0.4, 0.5]})
    assert len(configs) == 4

    def evaluate(cfg):
        return {"score": cfg["k"] + cfg["threshold"]}

    results = run_multiverse(configs, evaluate)
    assert len(results) == 4
    assert set(results.columns) >= {"k", "threshold", "score"}


def test_variance_decomposition():
    configs = enumerate_configurations({"a": [1, 2], "b": [10, 20]})

    def evaluate(cfg):
        # score driven mostly by a
        return {"ell": float(cfg["a"] * 10 + cfg["b"] * 0.01)}

    results = run_multiverse(configs, evaluate)
    shares = variance_decomposition(results, "ell", ["a", "b"])
    assert shares.iloc[0]["dimension"] == "a"
    assert shares.loc[shares.dimension == "a", "variance_share"].iloc[0] > 0.5
