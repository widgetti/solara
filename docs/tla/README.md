# TLA+ models of the solara server locks

`SolaraLocks.tla` models the locks in [../deadlock-rules.md](../deadlock-rules.md).
`SolaraLifecycle.tla` models the cull/reconnect race; `LifeFix.cfg` is the fix now in `kernel_context.py` (`_begin_close` under the decision lock).
Both event loops are modelled as mutexes: a coroutine that blocks holds its loop for that time.

## Run

Get `tla2tools.jar` from https://github.com/tlaplus/tlaplus/releases, then:

```
java -cp tla2tools.jar pcal.trans docs/tla/SolaraLocks.tla
java -XX:+UseParallelGC -cp tla2tools.jar tlc2.TLC -config docs/tla/New.cfg -workers auto docs/tla/SolaraLocks.tla
```

Re-run `pcal.trans` after every edit to the PlusCal block, or TLC checks the old translation.

## Configurations

| cfg | what it is |
|-----|------------|
| `New.cfg` | the current code. No deadlock, everything terminates. |
| `Old.cfg` | the code before the fixes. Both rules broken. |
| `OldEvict.cfg` | only rule 1 broken: evict closes on the uvicorn loop. |
| `OldStore.cfg` | only rule 2 broken: listeners fire under the store lock. |
| `OldCull.cfg` | one wedged handler, culls close on the shared keep-alive loop. |
| `NewCull.cfg` | the same wedged handler with the cull off the loop. |
| `NewWF.cfg` | `New.cfg` under weak fairness (`SpecWF`), which finishes in the time budget. |
| `LifeRace.cfg` / `LifeFix.cfg` | the lifecycle race, without and with the candidate fix (`SolaraLifecycle.tla`). |

## Fairness

Every process is `fair+` (strong fairness).
A thread blocked on a real mutex eventually gets it.
With plain weak fairness TLC reports a starvation lasso that is an artefact:
one thread takes the store lock briefly on every loop iteration, so a second thread waiting
for that lock is never *continuously* enabled and weak fairness never forces it to run.
Strong fairness costs time: the liveness pass dominates the run.
`New.cfg` under strong fairness did not finish inside 10 minutes, so use `NewWF.cfg`.
That is not a weaker result: weak fairness allows every behaviour strong fairness allows
and more, so a property that holds for `SpecWF` also holds for `Spec`.

TLC's built-in deadlock check is used as-is.
The PlusCal translator adds a `Terminating` stuttering step, so the all-Done state is not
reported as a deadlock; any other state with no enabled action is a real lock cycle.
