"""
The simulation is based on a grid where each cell
contains either no plant, a benign plant, or a weed.

No plant is encoded as zero.
The benign plant is encoded as 1.
The invasive plant (weed) is encoded as -1.

The invasive plant spreads from the top left
"""
from collections import namedtuple
from itertools import product

import numpy as np
import pandas as pd
import simpy

from plant_distribution import DATA_FOLDER

# %%
"""
# Simulate plant spread
"""
n = 100  # grid size
grid = np.zeros((n, n), dtype=int)

T = 5000  # planning horizon

avg_weed_life = 120  # days
avg_weed_proliferation_time = 50
weed_spread_range = 3

avg_plant_life = 300
avg_plant_proliferation_time = 300
plant_spread_range = 7

Event = namedtuple("Event", ["t", "species", "x", "y", "n_plants"])
event_history = []


class Plant:
    next_id = 0

    def __init__(self, env_, species: int, x_, y_,
                 avg_lifetime, avg_proliferation_time, max_spread_range):
        self.env = env_
        self.env.n_plants += 1
        self.species = species
        self.x = x_
        self.y = y_
        self.avg_lifetime = avg_lifetime
        self.avg_proliferation_time = avg_proliferation_time
        self.max_spread_range = max_spread_range
        self.id = Plant.next_id
        Plant.next_id += 1
        assert 0 <= x_ < n
        assert 0 <= y_ < n
        grid[self.x, self.y] = species
        print(f"{env_.now} - new {species} at ({x_}, {y_} - n = {env_.n_plants})")
        event_history.append(Event(env_.now, species, x_, y_, env_.n_plants))
        lifetime = np.random.geometric(1.0 / avg_lifetime)
        self.life_over_event = env_.timeout(lifetime)
        self.env.process(self.live_and_prosper())

    def live_and_prosper(self):
        while True:
            inter_arrival_time = np.random.geometric(1.0 / self.avg_proliferation_time)
            ret = yield self.env.timeout(inter_arrival_time) | self.life_over_event

            if self.life_over_event in ret:  # plant died
                grid[self.x, self.y] = 0
                self.env.n_plants -= 1
                event_history.append(Event(self.env.now, 0, self.x, self.y, self.env.n_plants))
                print(f"{self.env.now} - dead {self.species} at ({self.x}, {self.y}) - n = {self.env.n_plants}")
                break

            # plant potentially creates offspring
            offset_x = offset_y = 0
            while offset_x == 0 and offset_y == 0:
                offset_x, offset_y = np.random.randint(
                    low=-self.max_spread_range, high=self.max_spread_range + 1, size=2)
            new_x = min(max(self.x + offset_x, 0), n - 1)
            new_y = min(max(self.y + offset_y, 0), n - 1)

            if grid[new_x, new_y] == 0:
                # plant creates offspring
                Plant(self.env, self.species, new_x, new_y,
                      self.avg_lifetime, self.avg_proliferation_time, self.max_spread_range)


def run_sim():
    env = simpy.Environment()
    env.n_plants = 0

    # Place some benight plants
    probability_benign = 0.1
    xys = (np.random.rand(n, n) < probability_benign).astype(int)
    xys[0:4, 0:4] = 0  # keep free for weeds
    xs, ys = np.where(xys)
    for i, x in enumerate(xs):
        Plant(env, 1, x, ys[i], avg_plant_life, avg_plant_proliferation_time, plant_spread_range)

    # Plase some weeds in the top left
    for x, y in product(range(4), range(4)):
        Plant(env, -1, x, y, avg_weed_life, avg_weed_proliferation_time, weed_spread_range)

    env.run(until=T)

    # Store history
    df = pd.DataFrame(event_history)
    df.to_csv(DATA_FOLDER / "sim_history.csv")


# %%

if __name__ == "__main__":
    run_sim()
