# MAX-SAT Optimization Algorithms Implementation Guide

## Table of Contents

1. [Project Overview](#project-overview)
2. [Initialization Strategies](#initialization-strategies)
3. [Hill Climbing (HC)](#hill-climbing-hc)
4. [Simulated Annealing (SA)](#simulated-annealing-sa)
5. [Genetic Algorithm (GA)](#genetic-algorithm-ga)
6. [Binary Swarm Optimization (BSGO/POS)](#binary-swarm-optimization-bsgo)
7. [Hybrid BSGO-GA Algorithm](#hybrid-bsgo-ga-algorithm)
8. [Algorithm Comparison](#algorithm-comparison)
9. [Implementation Details](#implementation-details)

***

## Project Overview

This project implements and compares multiple metaheuristic algorithms for solving MAX-SAT (Maximum Satisfiability) problems on 3-CNF formulas. The goal is to find an assignment that maximizes the number of satisfied clauses.

**Problem Definition:**

- Given a Boolean formula in Conjunctive Normal Form (CNF)
- Each clause contains literals (variables or their negations) joined by OR
- MAX-SAT aims to maximize the number of satisfied clauses
- A clause is satisfied if at least one literal evaluates to TRUE

**Benchmark Parameters:**

- Variables: n ∈ {50, 100, 150, 200, 500}
- Clause density ratios: m/n ∈ {3.0, 4.3, 6.0}
- where m = number of clauses, n = number of variables

***

## Initialization Strategies

### Why Initialization Matters

Initialization is crucial because:

1. **Quality of initial solutions** directly impacts convergence speed
2. **Search space coverage** affects ability to find global optima
3. **Diversification** helps escape poor local optima
4. **Problem-specific knowledge** can bias searches favorably

### Our Initialization Approach

We use **purely random initialization** for all algorithms. This choice is deliberate and provides several advantages:

#### Random Binary Initialization

```python
def _random_truth_assignment(num_variables: int, rng: random.Random) -> TruthAssignment:
    return [rng.choice((False, True)) for _ in range(num_variables)]
```

**Rationale for Random Initialization:**

1. **Unbiased Starting Points**
   - No prior assumptions about problem structure
   - Equal probability for all possible assignments (2^n possibilities)
   - Avoids initialization bias that could skew results
2. **Simplicity and Reproducibility**
   - Easy to implement and debug
   - Random seed controls ensure reproducibility
   - No complex preprocessing required
3. **Theoretical Justification**
   - For random 3-SAT instances, no efficient heuristic exists for good initial assignments
   - Random initialization provides baseline performance
   - Allows fair comparison across algorithms
4. **Population-based Diversity**
   - In population-based algorithms (GA, BSGO), random initialization naturally creates diverse initial populations
   - Each individual starts with independent random assignment
   - Diversity is crucial for evolutionary algorithms

#### Initialization in Population-Based Algorithms

**Genetic Algorithm (GA):**

```python
population: List[TruthAssignment] = [
    [rng.choice((False, True)) for _ in range(n)] for _ in range(population_size)
]
```

- Each of the 56 individuals gets a completely random assignment
- Initial population diversity is maximized
- Ensures broad exploration of search space from the start

**Binary Swarm Optimization (BSGO):**

```python
population: List[TruthAssignment] = [
    [rng.choice((False, True)) for _ in range(n)] for _ in range(population_size)
]
continuous_state: List[List[float]] = [
    [(1.0 if bit else 0.0) + rng.uniform(-0.35, 0.35) for bit in individual]
    for individual in population
]
```

- Binary population initialized randomly
- Each particle gets continuous auxiliary state for sigmoid binarization
- Small random perturbations (±0.35) added to continuous values
- Allows immediate exploration of binary neighborhood

#### Why Not Greedy/Heuristic Initialization?

While greedy initialization (e.g., using clause satisfaction counts) might seem appealing:

**Arguments Against:**

1. **Computational overhead** - requires preprocessing
2. **Algorithm bias** - may favor certain regions of search space
3. **Loss of diversity** - reduced exploration capability
4. **Problem-specific tuning** - greedy heuristics are problem-dependent
5. **Fair comparison** - random initialization provides consistent baseline

**Our Conclusion:**
Random initialization is the most principled choice for:

- Theoretical analysis (no hidden bias)
- Empirical comparison (equal treatment across algorithms)
- General applicability (works for any SAT instance)

***

## Hill Climbing (HC)

### Algorithm Overview

Hill Climbing is a greedy local search algorithm that iteratively improves the solution by making single-variable flips that increase the number of satisfied clauses.

### Implementation Details

#### Core Strategy: Best-Improvement Hill Climbing

```python
def _select_best_improving_neighbor(formula, assignment, current_merit, rng):
    best_merit_after_flip = current_merit
    candidate_indices: List[int] = []
    
    for variable_index in range(formula.num_variables):
        merit_if_flipped = _merit_after_flip(formula, assignment, variable_index)
        if merit_if_flipped > best_merit_after_flip:
            best_merit_after_flip = merit_if_flipped
            candidate_indices = [variable_index]
        elif merit_if_flipped == best_merit_after_flip and merit_if_flipped > current_merit:
            candidate_indices.append(variable_index)
    
    if not candidate_indices:
        return None
    
    return rng.choice(candidate_indices)
```

#### Key Characteristics

1. **Best-Improvement vs. First-Improvement**
   - We use **best-improvement** strategy (examines all neighbors)
   - More thorough than first-improvement (stochastic) approach
   - Random selection among ties for diversification
2. **Single Flip Neighborhood**
   - Only one variable is flipped at a time
   - Neighborhood size: n possible moves
   - Incremental evaluation for efficiency
3. **Random Restarts**
   ```python
   for _restart_index in range(max_random_restarts):
       current_assignment = _random_truth_assignment(formula.num_variables, rng)
       # ... perform hill climbing ...
   ```
   - When stuck at local optimum, restart with new random assignment
   - Combines exploitation (within-run) with exploration (restarts)
   - Maximum of `max_random_restarts` restarts

#### Algorithm Flow

```
Initialize: Random truth assignment
while (not at local optimum) and (iterations < budget):
    1. Evaluate all n possible single-variable flips
    2. Select the flip that maximizes satisfied clauses
    3. If improving move exists:
       - Execute the flip
       - Update current merit
       - Record in history
    4. Else:
       - Stop (local optimum reached)
       - Start new restart if allowed

Return: Best assignment found across all restarts
```

#### Parameters

- `max_iterations_per_restart`: Maximum flips before forced restart (default: 1000)
- `max_random_restarts`: Number of fresh starts allowed (default: 10)
- `random_seed`: For reproducibility

#### Strengths and Weaknesses

**Strengths:**

- Simple to implement and understand
- Memory efficient (only current state)
- Fast per-iteration (greedy selection)
- Effective for easy instances

**Weaknesses:**

- Gets trapped in local optima
- No ability to escape even minor valleys
- Performance degrades near phase transition (m/n ≈ 4.26)

#### Why Best-Improvement Strategy?

We chose best-improvement over first-improvement because:

1. **Faster convergence** - always takes the most beneficial step
2. **More thorough search** - explores all neighbors before deciding
3. **Better solutions** - typically reaches better local optima
4. **Tie-breaking randomization** - maintains some diversity

***

## Simulated Annealing (SA)

### Algorithm Overview

Simulated Annealing is a probabilistic metaheuristic that escapes local optima by accepting worse solutions with a probability that decreases over time, inspired by the metallurgical annealing process.

### Implementation Details

#### Temperature Schedule

```python
def simulated_annealing_search(
    formula,
    max_iterations: int,
    initial_temperature: float,    # T₀ = 10.0
    cooling_rate: float,           # α = 0.9995
    min_temperature: float,        # T_min = 0.01
):
```

**Temperature Update:**

```python
temperature *= cooling_rate  # Multiplicative cooling
```

**Why This Cooling Schedule?**

1. **Multiplicative vs. Additive Cooling**
   - Multiplicative: T ← αT where α ∈ (0,1)
   - More gradual than additive cooling
   - Allows prolonged exploration in early stages
   - Enables fine-grained exploitation in later stages
2. **Parameter Selection Rationale**
   - `T₀ = 10.0`: High enough to accept most worse moves initially
   - `α = 0.9995`: Slow cooling (≈2000 iterations to reach T\_min)
   - `T_min = 0.01`: Practical termination threshold

#### Acceptance Criterion

```python
delta_merit = neighbor_merit - current_merit

if delta_merit >= 0:
    should_accept = True  # Always accept improvements
else:
    # Boltzmann probability: exp(ΔE/T)
    acceptance_probability = math.exp(delta_merit / temperature)
    if rng.random() < acceptance_probability:
        should_accept = True  # Probabilistically accept worse moves
```

**The Acceptance Probability:**

1. **Large temperature (early):**
   - T ≈ 10.0, small negative Δ ≈ -5
   - P ≈ exp(-5/10) = exp(-0.5) ≈ 0.61
   - High probability of accepting worse solutions
   - Enables exploration
2. **Small temperature (late):**
   - T ≈ 0.1, same Δ ≈ -5
   - P ≈ exp(-5/0.1) = exp(-50) ≈ 2×10⁻²²
   - Near-zero probability of accepting worse moves
   - Focused exploitation

#### Single-Flip Neighborhood

```python
flip_index = rng.randrange(formula.num_variables)
current_assignment[flip_index] = not current_assignment[flip_index]
```

**Rationale:**

- Simple, well-understood neighborhood
- Allows gradual improvement
- Large enough to guarantee connectivity (n-neighborhood)

#### Algorithm Flow

```
Initialize: Random assignment, T = T₀
iterations = 0

while iterations < max_iterations AND T > T_min:
    1. Generate random neighbor (flip one variable)
    2. Calculate Δ = new_merit - current_merit
    3. If Δ > 0: accept (always)
       Else if random() < exp(Δ/T): accept (probabilistically)
       Else: reject (keep current)
    4. Update current solution if accepted
    5. Track best solution found
    6. Record history
    7. T = α × T (cool down)
    8. iterations++

Return: Best assignment found
```

#### Parameters

- `max_iterations`: 5000 (allows thorough search)
- `initial_temperature`: 10.0 (allows substantial exploration)
- `cooling_rate`: 0.9995 (slow cooling schedule)
- `min_temperature`: 0.01 (practical termination)

#### Strengths and Weaknesses

**Strengths:**

- Escapes local optima through probabilistic acceptance
- Theoretically guaranteed to find global optimum (with infinite time)
- No parameters beyond temperature schedule
- Effective for rugged fitness landscapes

**Weaknesses:**

- Requires careful temperature tuning
- Slow convergence in late stages
- May waste iterations accepting bad moves near optimum
- Performance sensitive to cooling rate

#### Why Simulated Annealing?

1. **Exploration-Exploitation Balance**
   - Automatic transition from exploration to exploitation
   - High T: random walk behavior
   - Low T: greedy hill climbing behavior
2. **Theoretical Foundation**
   - Based on statistical mechanics (Metropolis algorithm)
   - Convergence guarantees with logarithmic cooling
   - Well-studied parameter sensitivity
3. **Empirical Success**
   - Proven effective on MAX-SAT
   - Works well near phase transition
   - Complement to deterministic methods

***

## Genetic Algorithm (GA)

### Algorithm Overview

Genetic Algorithm is an evolutionary algorithm that maintains a population of solutions and evolves them through selection, crossover, and mutation operators, mimicking natural evolution.

### Implementation Details

#### Population Initialization

```python
population_size = 56  # Population size
population: List[TruthAssignment] = [
    [rng.choice((False, True)) for _ in range(n)] for _ in range(population_size)
]
fitness = [compute_solution_merit(formula, individual) for individual in population]
```

**Why Population Size = 56?**

1. **Theoretical Considerations**
   - Too small: premature convergence
   - Too large: slow convergence, wasted computation
   - 56 provides good balance for n ∈ {50, 100, 200, 500}
2. **Empirical Studies**
   - Rule of thumb: 2-3× problem size for simple problems
   - For NK-landscapes and SAT, larger populations often help
   - 56 balances diversity with computational cost

#### Fitness Evaluation

```python
fitness = [compute_solution_merit(formula, individual) for individual in population]
best_idx = max(range(population_size), key=lambda i: fitness[i])
```

**Direct Clause Count as Fitness:**

- More satisfied clauses = better fitness
- Simple, interpretable objective
- Aligned with MAX-SAT goal
- No need for scaling or ranking

#### Selection: Tournament Selection

```python
def tournament_select() -> TruthAssignment:
    candidates = [rng.randrange(population_size) for _ in range(tournament_size)]
    winner = max(candidates, key=lambda idx: fitness[idx])
    return copy(population[winner])
```

**Why Tournament Selection?**

1. **Implicit Parallelism**
   - Doesn't require sorting
   - O(tournament\_size) per selection
   - Parallelizable
2. **Selective Pressure Control**
   - tournament\_size = 3 provides mild pressure
   - Larger tournaments increase selection pressure
   - Maintains diversity while favoring fit individuals
3. **Simplicity and Robustness**
   - No parameter tuning beyond tournament size
   - Works well across different problem types
   - Self-adaptive to population diversity

#### Crossover Operators

**One-Point Crossover:**

```python
cut = rng.randrange(1, n)
child = parent_a[:cut] + parent_b[cut:]
```

**Two-Point Crossover:**

```python
cut1 = rng.randrange(1, n - 1)
cut2 = rng.randrange(cut1 + 1, n)
child = parent_a[:cut1] + parent_b[cut1:cut2] + parent_a[cut2:]
```

**Why Both Operators?**

1. **Exploration vs. Exploitation**
   - One-point: preserves building blocks (schemata)
   - Two-point: better mixing, less positional bias
   - Both are commonly used in literature
2. **Crossover Rate = 0.88**
   - High rate promotes recombination
   - Allows exploration of new combinations
   - Still preserves some elite solutions

#### Mutation: Bit-Flip Mutation

```python
mutation_rate = min(0.04, 2.0 / max(formula.num_variables, 1))

for bit_idx in range(n):
    if rng.random() < mutation_rate:
        child[bit_idx] = not child[bit_idx]
```

**Adaptive Mutation Rate:**

1. **Formula: 2/n**
   - Standard mutation rate for binary representations
   - Ensures one mutation per individual on average
   - Scales with problem size
2. **Why This Formula?**
   - Maintains diversity without disrupting good solutions
   - Prevents premature convergence
   - Well-established in GA literature
3. **Maximum Cap at 0.04**
   - Prevents excessive mutation for small problems
   - For n=50: rate = min(0.04, 0.04) = 0.04
   - For n=500: rate = min(0.04, 0.004) = 0.004

#### Elite Preservation

```python
ranked_indices = sorted(range(population_size), key=lambda i: fitness[i], reverse=True)
next_population = [copy(population[idx]) for idx in ranked_indices[:elite_count]]
```

**Elite Count = 2:**

- Preserves best solutions unchanged
- Prevents regression
- Maintains best-found quality
- Minimal overhead

#### Complete Algorithm Flow

```
Initialize: Random population (56 individuals)
Evaluate: Compute fitness for all individuals
generations = 0

while generations < max_generations AND not optimal:
    1. Select parents using tournament selection (k=3)
    2. Perform crossover (88% probability):
       - One-point or two-point (randomly chosen)
       - Generate two children
    3. Apply bit-flip mutation to children
    4. Evaluate offspring fitness
    5. Select next generation:
       - Elitism: keep top 2 individuals
       - Fill rest with offspring
    6. Update best solution found
    7. generations++

Return: Best individual in final population
```

#### Parameters

- `population_size`: 56
- `max_generations`: 220
- `crossover_rate`: 0.88
- `mutation_rate`: min(0.04, 2/n)
- `elite_count`: 2
- `tournament_size`: 3
- `crossover_mode`: "two\_point" (default)

#### Strengths and Weaknesses

**Strengths:**

- Maintains population diversity
- Effective crossover combines good building blocks
- Parallelizable (population-based)
- Robust across problem types

**Weaknesses:**

- Many parameters to tune
- Slower per-generation than local search
- May converge to mediocre solutions
- Requires careful balance of operators

#### Why These GA Parameters?

1. **Population Size (56)**
   - Balances diversity and computational cost
   - Large enough to avoid premature convergence
   - Small enough for fast iterations
2. **Crossover Rate (0.88)**
   - High rate promotes recombination
   - Preserves some solutions unchanged
   - Empirical success on MAX-SAT
3. **Mutation Rate (2/n)**
   - Standard adaptive rate
   - Self-adjusts to problem size
   - Prevents stagnation
4. **Tournament Size (3)**
   - Low selection pressure
   - Maintains diversity
   - Simple to implement

***

## Binary Swarm Optimization (BSGO)

### Algorithm Overview

Binary Swarm Optimization is a particle swarm variant adapted for binary/discrete optimization. Particles explore the search space using continuous auxiliary states transformed via sigmoid functions.

### Implementation Details

#### Swarm Initialization

```python
population_size = 42  # Swarm size
population: List[TruthAssignment] = [
    [rng.choice((False, True)) for _ in range(n)] for _ in range(population_size)
]
continuous_state: List[List[float]] = [
    [(1.0 if bit else 0.0) + rng.uniform(-0.35, 0.35) for bit in individual]
    for individual in population
]
```

**Why Add Perturbations to Continuous State?**

1. **Initial Diversity in Continuous Space**
   - Binary population provides binary diversity
   - Continuous perturbations add exploration capability
   - Prevents all particles from starting at same continuous location
2. **Smooth Transition**
   - Initial sigmoid probabilities influenced by starting bits
   - ±0.35 perturbation allows both exploitation and exploration
   - Gradual learning process
3. **Why 42 Particles?**
   - Smaller than GA population (less computation)
   - Social learning more effective than crossover
   - Proven effective in PSO literature

#### Particle Update Rule

```python
for particle_idx in range(population_size):
    old_bits = population[particle_idx]
    old_fitness = fitness[particle_idx]
    old_continuous = continuous_state[particle_idx]
    
    candidate_continuous: List[float] = []
    candidate_bits: TruthAssignment = []
    
    for dim in range(n):
        social_noise = rng.uniform(0.0, 1.0)
        perturbation = rng.uniform(-0.15, 0.15)
        updated_value = (
            c_parameter * old_continuous[dim]
            + social_noise * (global_best_float[dim] - old_continuous[dim])
            + perturbation
        )
        candidate_continuous.append(updated_value)
        candidate_bits.append(rng.random() < _sigmoid(updated_value))
```

**Update Components:**

1. **Inertia Term: c × old\_continuous**
   - c = 0.72 (inertia weight)
   - Preserves particle's current trajectory
   - Controls exploration vs. exploitation
2. **Social Learning Term: noise × (gbest - old)**
   - Pulls particle toward global best
   - Stochastic noise for diversity
   - Range: uniform(0, 1) for noise
3. **Random Perturbation: ±0.15**
   - Local exploration capability
   - Prevents premature convergence
   - Adds randomness to all dimensions

**Why c = 0.72?**

1. **Standard PSO Range**
   - c ∈ (0, 1) typical for continuous PSO
   - Values > 1 may cause divergence
   - 0.72 provides balance
2. **Empirical Success**
   - Commonly used in binary PSO variants
   - Good convergence properties
   - Works well across problems

#### Sigmoid Transformation

```python
def _sigmoid(value: float) -> float:
    if value >= 30.0:
        return 1.0 - 1e-15
    if value <= -30.0:
        return 1e-15
    return 1.0 / (1.0 + math.exp(-value))
```

**From Continuous to Binary:**

1. **Sigmoid Probability**
   - Maps real values to (0, 1)
   - P(bit=1) = sigmoid(x)
   - Stochastic binarization preserves exploration
2. **Boundary Handling**
   - Values > 30: P ≈ 1
   - Values < -30: P ≈ 0
   - Numerical stability

#### Strict Improvement Acceptance

```python
candidate_fitness = compute_solution_merit(formula, candidate_bits)
if candidate_fitness >= old_fitness:
    population[particle_idx] = candidate_bits
    continuous_state[particle_idx] = candidate_continuous
    fitness[particle_idx] = candidate_fitness
    if candidate_fitness > global_best_merit:
        global_best_merit = candidate_fitness
        global_best = copy(candidate_bits)
```

**Key Design Choice:**

- Only accepts improving or equal moves
- No simulated annealing-style acceptance
- Simpler than BSGO variants with worse-accept
- Effective for MAX-SAT

#### Algorithm Flow

```
Initialize: Random binary population + continuous states
Evaluate: Compute fitness for all particles
global_best = best particle in population

for iteration in range(max_iterations):
    for each particle:
        1. Generate candidate continuous state:
           new = c × old + noise × (gbest - old) + perturbation
        2. Transform to binary via sigmoid
        3. Evaluate candidate fitness
        4. If candidate >= current:
           - Update particle position
           - Update continuous state
           - Update personal best if improved
           - Update global best if improved
    5. Record history
    6. Check termination

Return: Global best found
```

#### Parameters

- `population_size`: 42
- `max_iterations`: 260
- `c_parameter`: 0.72 (inertia weight)
- `social_noise_range`: \[0, 1]
- `perturbation_range`: \[-0.15, 0.15]

#### Strengths and Weaknesses

**Strengths:**

- Combines continuous and binary search
- Social learning is powerful
- Simple implementation
- Fast convergence

**Weaknesses:**

- Single global best may cause convergence
- Limited exploration compared to GA
- Parameter sensitivity
- No crossover-like recombination

#### Why Binary Swarm Optimization?

1. **Continuous-Binary Bridge**
   - PSO theory developed for continuous spaces
   - Sigmoid provides smooth binary transformation
   - Maintains swarm dynamics
2. **Social Learning**
   - Particles learn from global best
   - More efficient than GA crossover for some problems
   - Automatic intensification
3. **Simplicity**
   - Single update rule
   - No crossover operators
   - Easy to implement and tune

***

## Hybrid BSGO-GA Algorithm

### Algorithm Overview

The hybrid algorithm combines Binary Swarm Optimization's improving phase with Genetic Algorithm's crossover and mutation, leveraging the strengths of both approaches.

### Implementation Details

#### Algorithm Structure

The hybrid has two distinct phases per generation:

1. **Improving Phase (BSGO-style)**
   - Per-particle continuous update
   - Sigmoid binarization
   - Strict improvement acceptance
2. **Evolution Phase (GA-style)**
   - Tournament selection
   - One-point crossover
   - Bit-flip mutation
   - Elite preservation

#### Improving Phase

```python
for particle_index in range(population_size):
    old_bits = population[particle_index]
    old_merit = fitness[particle_index]
    old_float = [1.0 if bit else 0.0 for bit in old_bits]
    continuous: List[float] = []
    
    for dimension in range(n):
        r_noise = rng.random()
        value = c_coefficient * old_float[dimension] + r_noise * (
            gbest_float[dimension] - old_float[dimension]
        )
        continuous.append(value)
    
    candidate: TruthAssignment = []
    for dimension in range(n):
        probability = _sigmoid_probability(continuous[dimension])
        candidate.append(rng.random() < probability)
    
    candidate_merit = compute_solution_merit(formula, candidate)
    if candidate_merit > old_merit:
        population[particle_index] = candidate
        fitness[particle_index] = candidate_merit
        if candidate_merit > global_best_merit:
            global_best = copy(candidate)
            global_best_merit = candidate_merit
```

**Differences from Pure BSGO:**

1. **No Random Perturbation**
   - Only inertia + social learning
   - Cleaner exploration
2. **Strict Improvement Only**
   - Rejects equal moves (unlike pure BSGO)
   - More conservative updating
3. **Continuous Conversion**
   - Uses gbest\_float directly (not sigmoid)
   - More direct social influence

#### Evolution Phase

```python
new_population: List[TruthAssignment] = []
elite_index = max(range(population_size), key=lambda index: fitness[index])
new_population.append(copy(population[elite_index]))

while len(new_population) < population_size:
    parent_a = tournament_select()
    parent_b = tournament_select()
    
    if n >= 2 and rng.random() < crossover_rate:
        cut = rng.randrange(1, n)
        child = parent_a[:cut] + parent_b[cut:]
    else:
        child = copy(rng.choice((parent_a, parent_b)))
    
    for bit_index in range(n):
        if rng.random() < mutation_rate:
            child[bit_index] = not child[bit_index]
    
    new_population.append(child)

population = new_population[:population_size]
fitness = [compute_solution_merit(formula, individual) for individual in population]
```

**Evolution Components:**

1. **Elite Preservation**
   - Best individual copied unchanged
   - Maintains global best quality
2. **Tournament Selection**
   - k=3 tournament size
   - Ensures selection pressure
3. **One-Point Crossover**
   - Simpler than GA's two-point
   - Effective for BSGO population
4. **Mutation**
   - Standard bit-flip
   - Low probability

#### Why This Hybridization?

**Theoretical Justification:**

1. **Complementary Strengths**
   - BSGO: Local improvement, social learning
   - GA: Global exploration, recombination
   - Hybrid: Best of both worlds
2. **Two-Stage Search**
   - Improving phase: Refine solutions
   - Evolution phase: Explore new regions
   - Alternating phases prevent stagnation
3. **Population Diversity**
   - BSGO updates add new solutions
   - GA crossover creates novel combinations
   - Maintains diversity throughout search

**Practical Benefits:**

1. **Robustness**
   - BSGO may struggle on some instances
   - GA crossover provides alternative paths
   - Hybrid works well across diverse instances
2. **Controlled Exploration**
   - BSGO phase: intensive local search
   - GA phase: broad exploration
   - Balanced search strategy

#### Complete Algorithm Flow

```
Initialize: Random population + fitness evaluation
global_best = best individual

for generation in range(max_iterations):
    # Phase 1: Improving (BSGO-style)
    for each particle:
        1. Update continuous state using inertia + social learning
        2. Sigmoid binarization
        3. Accept if strictly improving
        4. Update global best if improved
    
    # Phase 2: Evolution (GA-style)
    1. Copy elite to new population
    2. Tournament select pairs
    3. One-point crossover (88%)
    4. Bit-flip mutation
    5. Evaluate new population
    6. Update global best
    
    # Record history and check termination

Return: Global best found
```

#### Parameters

- `population_size`: 42
- `max_iterations`: 260
- `c_coefficient`: 0.72
- `crossover_rate`: 0.88
- `mutation_rate`: min(0.04, 2/n)
- `tournament_size`: 3

#### Strengths and Weaknesses

**Strengths:**

- Combines local and global search
- More robust than either alone
- Balances exploitation and exploration
- Proven effective on MAX-SAT

**Weaknesses:**

- More complex implementation
- More parameters to tune
- May be slower than pure methods
- Parameter interactions

***

## Algorithm Comparison

### Initialization Comparison

| Algorithm | Initialization      | Diversity                     | Rationale                   |
| --------- | ------------------- | ----------------------------- | --------------------------- |
| HC        | Random              | N/A (single solution)         | Baseline comparison         |
| SA        | Random              | N/A (single solution)         | Equal footing with HC       |
| GA        | Random population   | High (56 individuals)         | Maximum initial diversity   |
| BSGO      | Random + continuous | Medium-high (42 + continuous) | Balance exploration         |
| Hybrid    | Random population   | High (42 + 2 phases)          | Diversity from both methods |

### Search Strategy Comparison

| Algorithm | Exploration          | Exploitation       | Escapes Local Optima    |
| --------- | -------------------- | ------------------ | ----------------------- |
| HC        | Random restarts      | Greedy improvement | Limited (restarts only) |
| SA        | Probabilistic        | Greedy + cooling   | Yes (probabilistic)     |
| GA        | Crossover + mutation | Selection          | Yes (population-based)  |
| BSGO      | Continuous + sigmoid | Social learning    | Moderate (global best)  |
| Hybrid    | Both BSGO + GA       | Both               | Yes (dual mechanism)    |

### Parameter Sensitivity

| Algorithm | Key Parameters            | Sensitivity | Tuning Difficulty |
| --------- | ------------------------- | ----------- | ----------------- |
| HC        | Restart count, iterations | Low         | Easy              |
| SA        | T₀, cooling rate, T\_min  | High        | Moderate          |
| GA        | Pop size, rates           | Moderate    | Moderate          |
| BSGO      | c\_parameter              | Moderate    | Moderate          |
| Hybrid    | Multiple                  | Moderate    | Harder            |

***

## Implementation Details

### Data Structures

#### Truth Assignment

```python
TruthAssignment = List[bool]  # Binary vector
```

#### Fitness Function

```python
def compute_solution_merit(formula: CNFFormula, assignment: TruthAssignment) -> int:
    return sum(1 for clause in formula.clauses if is_clause_satisfied(clause, assignment))
```

#### Formula Structure

```python
@dataclass(frozen=True)
class CNFFormula:
    num_variables: int      # n
    clauses: Tuple[Clause, ...]  # m clauses

Clause = Tuple[Literal, ...]
Literal = NamedTuple('Literal', [('variable_index', int), ('is_negated', bool)])
```

### Performance Considerations

1. **Incremental Evaluation**
   - HC evaluates all neighbors but reuses previous evaluation
   - SA uses single-flip neighborhood
   - GA evaluates entire population each generation
2. **Memory Efficiency**
   - Single-solution algorithms (HC, SA): O(n)
   - Population algorithms: O(population\_size × n)
   - BSGO continuous state: additional O(population\_size × n)
3. **Parallelization Potential**
   - GA: Evaluate individuals in parallel
   - BSGO: Update particles in parallel
   - Hybrid: Both phases parallelizable

### Reproducibility

All algorithms use seeded random number generators:

```python
rng = random.Random(random_seed)  # All randomness from this RNG
```

This ensures:

- Identical results on repeated runs
- Fair algorithm comparison
- Debugging capability

***

## Conclusion

This implementation provides a comprehensive comparison of metaheuristic algorithms for MAX-SAT optimization. Each algorithm has been carefully designed with:

1. **Random initialization** for unbiased starting points
2. **Problem-appropriate neighborhood structures**
3. **Balanced exploration-exploitation tradeoffs**
4. **Reproducible behavior via seeded RNG**

The hybrid approach demonstrates how combining multiple metaheuristics can leverage their complementary strengths, while the standalone implementations provide baselines for comparison.

### Key Takeaways

- **Initialization matters**: Random initialization provides fair comparison
- **No free lunch**: Different algorithms excel on different instances
- **Hybridization helps**: Combining methods can outperform either alone
- **Parameter tuning is crucial**: Each algorithm has critical parameters
- **Problem structure matters**: Instance characteristics affect algorithm success

