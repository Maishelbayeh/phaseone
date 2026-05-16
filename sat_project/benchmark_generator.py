from __future__ import annotations

import json
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Iterable, List, Sequence

from config import (
    SA_STRESS_DENSITY_RATIOS,
    SA_STRESS_INSTANCE_DIR,
    SA_STRESS_INSTANCES_PER_CELL,
    SA_STRESS_VARIABLE_COUNTS,
)
from sat_generator import compute_clause_count_from_density, generate_3sat_instance


@dataclass(frozen=True)
class GeneratedInstanceRecord:
    instance_name: str
    n: int
    m: int
    ratio: float
    generator_seed: int
    instance_index: int
    file_path: str


def _instance_filename(n: int, ratio: float, instance_index: int) -> str:
    return f"3sat_n{n}_r{ratio:g}_i{instance_index:02d}.json"


def generate_sa_stress_instances(
    *,
    output_dir: Path = SA_STRESS_INSTANCE_DIR,
    variable_counts: Sequence[int] = SA_STRESS_VARIABLE_COUNTS,
    density_ratios: Sequence[float] = SA_STRESS_DENSITY_RATIOS,
    instances_per_cell: int = SA_STRESS_INSTANCES_PER_CELL,
    base_seed: int = 42,
) -> List[GeneratedInstanceRecord]:
    output_dir.mkdir(parents=True, exist_ok=True)
    records: List[GeneratedInstanceRecord] = []
    for n in variable_counts:
        for ratio in density_ratios:
            m = compute_clause_count_from_density(n, ratio)
            for instance_index in range(instances_per_cell):
                generator_seed = (
                    base_seed
                    + n * 1_000_003
                    + int(round(ratio * 100)) * 10_007
                    + instance_index * 100_009
                )
                file_name = _instance_filename(n, ratio, instance_index)
                file_path = output_dir / file_name
                if not file_path.exists():
                    payload = generate_3sat_instance(n=n, ratio=ratio, seed=generator_seed)
                    with file_path.open("w", encoding="utf-8") as file_obj:
                        json.dump(payload, file_obj, indent=2)
                records.append(
                    GeneratedInstanceRecord(
                        instance_name=file_name,
                        n=n,
                        m=m,
                        ratio=float(ratio),
                        generator_seed=generator_seed,
                        instance_index=instance_index,
                        file_path=str(file_path),
                    )
                )
    manifest_path = output_dir / "manifest.json"
    with manifest_path.open("w", encoding="utf-8") as file_obj:
        json.dump([asdict(record) for record in records], file_obj, indent=2)
    return records


def records_to_rows(records: Iterable[GeneratedInstanceRecord]) -> List[dict]:
    return [asdict(record) for record in records]
