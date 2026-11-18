from dataclasses import dataclass
import numpy as np


@dataclass(frozen=True)
class GenesisConfig:
    width: int = 128
    height: int = 128
    initial_min: float = 0.0
    initial_max: float = 1.0
    seed: int = 20261101
    steps: int = 500
    diffusion: float = 0.15
    noise_amplitude: float = 0.01


class GenesisZero:
    """
    GENESIS ZERO 0.1

    Experimental discrete field.
    This is an abstract computational model,
    not a physical cosmological simulation.
    """

    def __init__(self, config: GenesisConfig):
        self.config = config
        self.rng = np.random.default_rng(config.seed)

        self.state = self.rng.uniform(
            config.initial_min,
            config.initial_max,
            (config.height, config.width)
        )

        self.step = 0

    def evolve(self):
        current = self.state

        neighbors = (
            np.roll(current, 1, axis=0)
            + np.roll(current, -1, axis=0)
            + np.roll(current, 1, axis=1)
            + np.roll(current, -1, axis=1)
        ) / 4.0

        noise = self.rng.normal(
            0.0,
            self.config.noise_amplitude,
            current.shape
        )

        updated = (
            current
            + self.config.diffusion * (neighbors - current)
            + noise
        )

        self.state = updated
        self.step += 1

        return self.state

    def observe(self):
        return {
            "step": self.step,
            "minimum": float(np.min(self.state)),
            "maximum": float(np.max(self.state)),
            "mean": float(np.mean(self.state)),
            "std": float(np.std(self.state)),
            "variance": float(np.var(self.state)),
            "total": float(np.sum(self.state)),
        }


if __name__ == "__main__":
    config = GenesisConfig()
    universe = GenesisZero(config)

    print("GENESIS ZERO 0.1")
    print("Initial state:", universe.observe())

    for _ in range(config.steps):
        universe.evolve()

    print("Final state:", universe.observe())
