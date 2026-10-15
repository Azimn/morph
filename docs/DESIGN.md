# Developmental runtime contract

## Turn semantics

Input is JSON-compatible and validated before time advances. Duplicate observation IDs are rejected across resumed sessions. Nonfinite costs, negative costs, backward clocks, unknown channels, invalid action steps, and ambiguous task IDs are rejected. The environment evaluator must own observations: passing conversational requests directly into this field would let a user or model manufacture growth pressure.

A successful turn advances the counter and wall-clock value, replaces the transient scratchpad, credits the per-turn reserve, then prunes inactive or unaffordable structures and charges maintenance for survivors. Probes and processing see only that surviving topology. Observed friction increases absent-organ gradients and deducts failure penalties. Mounted organs process the current input, the audit mirror records current arbiter choices, and the engineer log captures the result. Finally the engine mounts affordable threshold-crossing organs and issues genesis receipts. New organs begin processing on the next turn. A probe and same-turn genesis therefore cannot contradict each other.

Pruning occurs before a dormant organ can use a new input. Reactivation after expiry requires fresh developmental pressure. A gradient accumulated before pruning may permit immediate regrowth, but regrowth starts with empty organ state. Routine empty processing calls do not count as useful work. Maintenance is charged from the reserve in catalog-ID sort order; this tie-breaker is deterministic and is a model assumption, not an evolved priority policy.

## Accounting

For absent organ channel k, each accepted externally scored observation adds its cost to G_k. Growth requires G_k >= threshold_k and reserve >= compile_cost_k + tax_k. Compilation deducts its fixed cost and resets that channel's gradient. The next turn starts paying its maintenance. Observations received while the corresponding organ is mounted remain in the engineer log and incur failure penalties, but do not accumulate a new growth gradient.

The reserve is credited by budget_per_turn up to reserve_cap and depleted by failure penalties, compilation, maintenance, and explicit Chronos ticks. Task selection has a separate per-turn action limit equal to budget_per_turn. Task cost constrains selection; the host must execute selected actions and account for real resources. These quantities are synthetic units. No claim is made that the ledger measures real CPU, energy, or inference tokens.

Gradients saturate at 1e100 to prevent overflow. Genesis events reference the latest contributing friction hash, preserve the cumulative gradient and thresholds, and are linked into the audit chain. All earlier contributions remain in the engineer audit. Rebirth appends a new genesis event; no earlier receipt is overwritten.

## Persistence boundary

The JSON snapshot is versioned and atomically replaced after flush and fsync of the file. Failed replacement preserves the previous snapshot. Snapshots are single-writer trusted-local artifacts and should be protected like conversation data. There is no multi-process locking, distributed synchronization, directory-fsync crash guarantee, encrypted store, or remote authenticity anchor.

A snapshot restores only mounted allowlisted classes. Empty zygote restoration does not import organ classes. The engineer log verifies its hash chain before restoration. The snapshot checksum covers resource state, topology, organ content, renderer style, growth-control setting, and audit history. It is not a digital signature. Unknown versions, corrupt checksums, unknown organ IDs, invalid counters, and invalid resource bounds fail closed.

The audit is not a subject memory organ. Organs receive the current input, clock, turn, and budget, never the audit log or arbitrary prior conversation. A host that injects old audit content into input would invalidate the no-history test. The implementation is a trusted single-process harness; Python objects can be inspected by privileged callers.

## Scientific interpretation

The six templates form an authored developmental genome. The topology assay tests environment-contingent instantiation and maintenance inside that genome. It does not distinguish this model from a well-built resource-aware plugin allocator, establish irreversible schema incompatibility, or prove novel architectural synthesis.

The benchmark contains three deterministic environments and matched growth-disabled versions, each run for 30 sessions. Logistics checks delayed recall and due events, optimization checks budget collisions and repeated pure trajectories, and household checks partner-record availability and prospective trace retrieval. Environment IDs are never supplied as growth instructions. Environment-specific task checks assign the channel and severity, so observer-design bias remains a central limitation.

Stronger evidence needs held-out environments, shuffled pressure order, measured-resource costs, a cost-matched fixed-topology control, a randomized-growth control, competing candidate structures, and repeated stochastic trials. The current deterministic identical-seed result establishes reproducibility, not a population effect or statistical significance. A fixed planner may perform equally well or better.

## Integration direction

Keep M.O.R.P.H. character-agnostic. A future Pretorius host can supply identity and validated first-person observations while retaining raw lifecycle records in its engineer channel. No Pretorius runtime, existing organ, or remote repository is modified by this release. A live language renderer should be added only alongside independent claim verification and adversarial hallucination tests. Prompts or first-person verb filters alone cannot enforce semantic entailment.
