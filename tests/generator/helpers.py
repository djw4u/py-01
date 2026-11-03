"""Hilfen für die Generator-Tests."""

import random

from py01.generator.params import Params


def parse(raw: str) -> Params:
    return Params.parse(raw)


def src(seed: int = 1) -> random.Random:
    return random.Random(seed)
