# Journal Clarity Reviewer report

## Scope
Main-paper and supplementary structure, readability, notation, cross-references, caption self-containment, and journal presentation.

## Findings

### Major — terminology and notation reference aid
The central terms and the paired sets $K_j$/$J_k$ deserve a compact notation/terminology aid near their first use. Define node ranges for $t_{ij}$ and the relationship $J_k = \{j : k \in K_j\}$ directly.

### Major — clarify main/supplement division
The supplement currently contains the full model, oracle pseudocode, numerical-safeguard detail, and extended results. Add a brief index/roadmap and say which sections are essential for reproducibility versus extended derivation.

### Major — make captions self-contained
Expand captions for the family table and the two figures to define non-obvious encodings (gap-tier boundaries, alpha/budget interpretation, and coverage labels). Repeat the runtime-comparability caveat in the BPC table note.

### Minor — abstract density
The abstract is technically dense. Shorter problem/method/results paragraphs would improve accessibility without changing claims.

### Minor — terminology consistency
Choose one spelling convention for synchronisation/synchronization and standardize acronyms on first use. Keep the certified-gap, BPC-gap, and objective-difference conventions visibly distinct.

### Minor — cross-reference titles
When pointing to supplementary algorithms, include both the algorithm number and its title on first mention.

## Strengths
The main paper has a conventional COR flow and the supplement successfully holds detailed derivations and robustness material outside the main narrative.

## Priority
Address notation, supplement navigation, and caption self-containment as the next editorial pass.