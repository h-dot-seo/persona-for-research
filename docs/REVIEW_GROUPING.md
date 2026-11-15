# Call-local review grouping

This implements roadmap #85 reviewer adjustment 9: `review_package.render`
previously scanned all topic-matched rules for every application pattern. A
private call-local index now groups eligible rules by the exact `(method,
condition)` strings. Buckets retain the original rule order and duplicates;
application pattern order is unchanged. This is not method selection, ranking,
source verification, semantic grouping, or a new cache.

`checked_package` and `apply` still execute freshly, once each, in their original
order. Source validation is neither skipped nor reused. Existing rendering,
options, error messages, detached-record checks and evidence judgments remain
on their original paths. There is no CI, timeout or persistence change.

## Conservative eligibility, not a new input restriction

Before validation can invoke custom Python behavior, a fixed eligibility result
is recorded for all inputs. Only exact built-in JSON trees qualify: dicts with
exact string keys, lists, strings, integers, booleans, null and finite floats.
Container aliases, cycles, subclasses, non-string keys and custom values fall
back to the original nested scan. Type identity checks do not call custom
metaclass equality, iteration, conversion or comparison methods. A custom value
that becomes plain during validation cannot open this optimization later.

After validation, both the package and fresh application are checked again.
The application must be an exact dict; rule/pattern collections must be exact
lists and their rows exact dicts. Missing or nonstandard shapes fall back without
new indexing/get errors, including substituted validation/application functions.
Method and condition keys must be exact strings. Each guard has a 100,000-value
node budget (with pending-child capacity checked before adding children); dict
keys are checked separately. This is only an optimization budget: exceeding it
returns to the old path without rejecting or normalizing the input. It is not
a new product size limit, a concurrency guarantee or complete hostile-memory
mutation defense.

## Measured synthetic work, not a speed promise

The opt-in experiment below builds N synthetic papers through the public build
API, each with one distinct method and two reasoning components. It compares
complete UTF-8 output against the same renderer forced down its original scan.
It observes Python line events and restores tracing afterwards. The guard
counts, rule visits and string-key shape checks are **different units**; do not
sum them into a speed or total-work claim. Validation and other rendering work
are unchanged and are not included in this table.

| N | Previous candidate rule visits | Bucket construction rule visits | New candidate visits | Guard value-node visits (all three guards) | Guard dict-key visits | Key-shape field checks |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 32 | 1024 | 32 | 32 | 8064 | 7083 | 128 |
| 128 | 16384 | 128 | 128 | 31872 | 28011 | 512 |
| 512 | 262144 | 512 | 512 | 127104 | 111723 | 2048 |

Package JSON sizes were 76,875 / 305,960 / 1,222,568 bytes; complete output sizes
were 18,286 / 71,176 / 283,528 UTF-8 bytes. All three output comparisons matched.
The additional row-type checks visit 64 / 256 / 1024 rows respectively,
separately from the two key-shape field checks per row. Two exact-container
checks and a combined 100,000-row eligibility cap also precede these checks.
These richer synthetic fixtures differ from the earlier investigation's minimal
one-observation records; its historical measurements are not rewritten.

The automatic regression uses only N=4. Larger measurements are opt-in:

```python
from tests.test_review_grouping import synthetic, measured
for n in (32, 128, 512):
    package = synthetic(n)
    old_text, before = measured(package, fallback=True)
    new_text, after = measured(package)
    assert old_text.encode('utf-8') == new_text.encode('utf-8')
    print(n, before, after)
```

The extra guards can outweigh savings on small inputs. This is a bounded
reduction of repeated rule scanning on eligible inputs, not a general linear
runtime or elapsed-time improvement claim. The two-seed CLI regression captures
raw stdout/stderr bytes, not newline-normalized text. Existing outputs, examples,
source records and scientific/approval meanings are unchanged.
