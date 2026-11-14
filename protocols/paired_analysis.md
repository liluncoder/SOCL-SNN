# Paired analysis

How two conditions are compared in this project. The short version: pair by seed, quote
the effect against seed noise, and never report a null without a minimum detectable effect.

## 1. Pair by seed

Both arms run the same seed set. The unit of analysis is the **difference within a seed**,
not the difference of two means.

Report, for every comparison:

- the per-seed differences `Δ_1 … Δ_n`;
- the sign count (how many are positive, negative, exact tie);
- `mean(Δ)` and `SD(Δ)`;
- the effect against seed noise: `mean(Δ) / SD(Δ)`;
- the MDES at this `n`, and whether the criterion was above it.

A mean and a `t` alone are not enough. The sign count is what reveals a distribution with
two catastrophic seeds; the ratio to `SD` is what distinguishes a mechanism from arithmetic.

## 2. Never pool the SD across arms

The noise term is the SD of the **within-seed differences**. A pooled across-arm SD
contains between-arm variance, which inflates the denominator and manufactures "no
difference" out of a real one.

This is the single most common way a paired design loses its power without anyone noticing.

## 3. Single seed does not count

One seed can carry a result, and a second seed can erase it. Two arms compared on one seed
each is an anecdote, however large the difference.

Replication cuts both ways, which is why it is required rather than encouraged: it can kill
a claim, and it can also upgrade a claim — "did not cross the threshold" becomes
"indistinguishable from zero" when the effect is inside the seed spread.

## 4. Do not drop seeds after looking

A catastrophic seed is part of the distribution you are measuring. Removing it improves the
effect and destroys the result.

If a seed is genuinely broken (a crash, a NaN, a misconfiguration), that is a void round
with a recorded reason — not a filtered one.

## 5. Every null carries its MDES

```
SE   ≈ σ_Δ / √n
MDES ≈ k · SE          quote k
```

A null without an MDES is unfalsifiable: it cannot be distinguished from a run that was too
small to see anything. When the MDES is larger than the effect being hunted, the correct
statement is **"this design could not have detected it"**, not "it is not there".

Two corollaries:

- If MDES ≤ δ (the equivalence margin) and the comparison is still undecided, power is not
  the bottleneck — the effect sits in the grey band, and that is worth saying explicitly.
- If MDES > δ, the equivalence claim is not available at all.

## 6. Report per subset, not per vector

When the mechanism can only reach part of the state, report the change over that part and
over the whole thing, each with its denominator.

The two numbers can differ by an order of magnitude and both be correct. Quoting only the
whole-vector number reads as "nothing happened"; quoting only the reachable-subset number
reads as "everything changed". Neither alone is honest.

## 7. Readout resolution before threshold

Compute the resolution of the readout (`1/n` for an accuracy over `n` scored rounds) and
write it next to the threshold. A threshold finer than the resolution is a coin flip; a
threshold inside the observed spread is a coin flip with a lab coat.

## Checklist

- [ ] Per-seed Δ reported, not just means
- [ ] Sign count reported
- [ ] Noise term is `SD(Δ)`, not a pooled SD
- [ ] Effect quoted as `mean/SD`
- [ ] MDES quoted with `k`, and compared to the threshold
- [ ] No seeds removed after inspection
- [ ] Subset and whole-vector changes both reported, with denominators
