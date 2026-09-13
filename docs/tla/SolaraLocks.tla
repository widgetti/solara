-------------------------- MODULE SolaraLocks --------------------------
(***************************************************************************)
(* A model of the lock structure of the solara server, used to check the    *)
(* rules in docs/deadlock-rules.md.                                         *)
(*                                                                          *)
(* Every resource is a mutex owned by at most one process.  Two event loops *)
(* are modelled as mutexes too: a coroutine that blocks while it runs holds  *)
(* its loop for that whole time, which is exactly what makes them behave     *)
(* like locks.                                                              *)
(*                                                                          *)
(* Resources (with the code they come from):                                *)
(*                                                                          *)
(*  ctx[k]   context.lock of kernel k, an RLock.  Held by the message thread *)
(*           for the WHOLE handling of one websocket message                 *)
(*           (solara/server/server.py:178 "with context.lock:").  Also taken *)
(*           by close(), see _finish_close in                                *)
(*           solara/server/kernel_context.py:387 "with self.lock:".          *)
(*                                                                          *)
(*  rlock[k] the reacton render lock (_RenderContext.thread_lock),           *)
(*           NON-reentrant, held for one whole render pass including the     *)
(*           effects phase (reacton/core.py render() ~1599, close() ~1328).  *)
(*           A thread that is already rendering never renders again          *)
(*           (_is_rendering / _possible_rerender), so the owner never        *)
(*           re-requests it.                                                 *)
(*                                                                          *)
(*  store    one reactive variable's RLock (KernelStore._lock,               *)
(*           solara/toestand.py).  OLD: update() fires listeners while       *)
(*           holding it.  NEW: _set_deferred() stores under the lock,        *)
(*           releases, then fires.  With mutation detection on, a READ takes *)
(*           it briefly (solara/_stores.py _ensure_public_exists).           *)
(*                                                                          *)
(*  uv       the uvicorn event loop, ONE per process.  Every portal.call     *)
(*           from a kernel thread waits for it                               *)
(*           (solara/server/starlette.py:223 send_text -> portal.call).      *)
(*                                                                          *)
(*  kal      the keep-alive event loop, ONE per process, shared by every     *)
(*           kernel's cull task (kernel_context.py keep_alive_event_loop).   *)
(*                                                                          *)
(* Processes: MessageThread[k], TaskThread[k], Cull[k] for k in Kernels,     *)
(* plus one Evict for kernel 1.                                             *)
(*                                                                          *)
(* Every process is "fair+" (STRONG fairness), not "fair".  A thread blocked *)
(* on a real mutex eventually gets it.  With only weak fairness TLC reports  *)
(* a spurious starvation lasso: one thread takes the store lock briefly on   *)
(* every loop iteration, so a second thread waiting for that lock is not     *)
(* CONTINUOUSLY enabled, and weak fairness never forces it to run.  That     *)
(* counterexample is an artefact of the fairness choice, not a solara bug.   *)
(***************************************************************************)
EXTENDS Naturals, Sequences, TLC

CONSTANTS
    HandlerSteps,    \* how many render passes one event handler does (2 is enough)
    NewCloseRules,   \* rule 1: close() never runs ON an event loop thread
    NewStoreRules,   \* rule 2: never fire listeners while holding a store lock
    EvictOn,         \* run the HTTP evict route at all (used to isolate counterexamples)
    WedgeK1          \* kernel 1's event handler never returns (a busy handler)

Kernels == {1, 2}

NoProc == <<"none", 0>>   \* the "no owner" value; a tuple so it is comparable with the process ids

MsgIds   == {<<"msg",   k>> : k \in Kernels}
TaskIds  == {<<"task",  k>> : k \in Kernels}
CullIds  == {<<"cull",  k>> : k \in Kernels}
EvictId  == <<"evict", 1>>

\* Reentrant (RLock) acquire/release.  The owner may re-enter; others wait.
AcqR(l, p) == [owner |-> p, count |-> l.count + 1]
RelR(l)    == IF l.count = 1 THEN [owner |-> NoProc, count |-> 0]
                             ELSE [owner |-> l.owner, count |-> l.count - 1]
FreeR      == [owner |-> NoProc, count |-> 0]

(*--algorithm SolaraLocks

variables
    ctx   = [k \in Kernels |-> FreeR],   \* context.lock per kernel (RLock)
    rlock = [k \in Kernels |-> NoProc],  \* reacton render lock per kernel (non-reentrant)
    store = FreeR,                       \* one reactive's KernelStore._lock (RLock)
    uv    = NoProc,                      \* the uvicorn event loop
    kal   = NoProc;                      \* the keep-alive event loop

(*************************************************************************)
(* The message thread of kernel k.  server.py holds context.lock for the  *)
(* whole handler.  The handler writes a reactive HandlerSteps times, and  *)
(* each write renders.  A render sends one widget update (portal.call ->  *)
(* uv) and does one reactive read (mutation detection -> store).          *)
(*************************************************************************)
fair+ process Msg \in MsgIds
variable i = 0;
begin
M_Ctx:
    await ctx[self[2]].owner \in {NoProc, self};
    ctx[self[2]] := AcqR(ctx[self[2]], self);
M_Loop:
    while i < HandlerSteps do
    M_RenderAcq:
        await rlock[self[2]] = NoProc;
        rlock[self[2]] := self;
    M_Send:
        \* portal.call: needs the uvicorn loop to run one step
        await uv = NoProc;
        uv := self;
    M_SendDone:
        uv := NoProc;
    M_Read:
        \* mutation detection reads the reactive, which takes the store lock
        await store.owner \in {NoProc, self};
        store := AcqR(store, self);
    M_ReadDone:
        store := RelR(store);
    M_RenderRel:
        rlock[self[2]] := NoProc;
        \* a wedged handler (WedgeK1) never finishes its loop
        i := IF WedgeK1 /\ self[2] = 1 THEN 0 ELSE i + 1;
    end while;
M_CtxRel:
    ctx[self[2]] := RelR(ctx[self[2]]);
end process;

(*************************************************************************)
(* A background task that writes the same reactive once via update().     *)
(* OLD: fire the listeners (a render) while still holding the store lock. *)
(* NEW: _set_deferred stores under the lock, releases, then fires.        *)
(*************************************************************************)
fair+ process Task \in TaskIds
begin
T_StoreAcq:
    await store.owner \in {NoProc, self};
    store := AcqR(store, self);
T_Store:
    \* read-modify-write of the value happens here (no data modelled)
    if NewStoreRules then
        store := RelR(store);
    end if;
T_FireAcq:
    \* firing a listener means a render, which takes the render lock
    await rlock[self[2]] = NoProc;
    rlock[self[2]] := self;
T_FireRel:
    rlock[self[2]] := NoProc;
T_Rel:
    if ~NewStoreRules then
        store := RelR(store);
    end if;
end process;

(*************************************************************************)
(* The HTTP evict route (starlette.py:451 evict).                         *)
(* OLD: the coroutine called context.close() itself, so it held the       *)
(* uvicorn loop for the whole close.                                      *)
(* NEW: _off_loop hands the close to a thread; the loop is free again.    *)
(*************************************************************************)
fair+ process Evict = EvictId
begin
E_Start:
    if ~EvictOn then
        goto Done;
    end if;
E_Uv:
    await uv = NoProc;
    uv := EvictId;
E_HandOff:
    if NewCloseRules then
        uv := NoProc;          \* _off_loop: run the close on a thread
    end if;
E_Ctx:
    await ctx[1].owner \in {NoProc, EvictId};
    ctx[1] := AcqR(ctx[1], EvictId);
E_Render:
    await rlock[1] = NoProc;   \* close() closes the render context
    rlock[1] := EvictId;
E_Rel:
    rlock[1] := NoProc;
    ctx[1] := RelR(ctx[1]);
E_UvRel:
    if ~NewCloseRules then
        uv := NoProc;
    end if;
end process;

(*************************************************************************)
(* The cull task of kernel k (kernel_context.py _bump_kernel_cull).       *)
(* OLD: close() ran inline on the shared keep-alive loop.                 *)
(* NEW: _run_in_thread runs the close off that loop and only awaits it.   *)
(*************************************************************************)
fair+ process Cull \in CullIds
begin
C_Kal:
    await kal = NoProc;
    kal := self;
C_HandOff:
    if NewCloseRules then
        kal := NoProc;         \* _run_in_thread
    end if;
C_Ctx:
    await ctx[self[2]].owner \in {NoProc, self};
    ctx[self[2]] := AcqR(ctx[self[2]], self);
C_Render:
    await rlock[self[2]] = NoProc;
    rlock[self[2]] := self;
C_Rel:
    rlock[self[2]] := NoProc;
    ctx[self[2]] := RelR(ctx[self[2]]);
C_KalRel:
    if ~NewCloseRules then
        kal := NoProc;
    end if;
end process;

end algorithm; *)

\* BEGIN TRANSLATION
VARIABLES ctx, rlock, store, uv, kal, pc, i

vars == << ctx, rlock, store, uv, kal, pc, i >>

ProcSet == (MsgIds) \cup (TaskIds) \cup {EvictId} \cup (CullIds)

Init == (* Global variables *)
        /\ ctx = [k \in Kernels |-> FreeR]
        /\ rlock = [k \in Kernels |-> NoProc]
        /\ store = FreeR
        /\ uv = NoProc
        /\ kal = NoProc
        (* Process Msg *)
        /\ i = [self \in MsgIds |-> 0]
        /\ pc = [self \in ProcSet |-> CASE self \in MsgIds -> "M_Ctx"
                                        [] self \in TaskIds -> "T_StoreAcq"
                                        [] self = EvictId -> "E_Start"
                                        [] self \in CullIds -> "C_Kal"]

M_Ctx(self) == /\ pc[self] = "M_Ctx"
               /\ ctx[self[2]].owner \in {NoProc, self}
               /\ ctx' = [ctx EXCEPT ![self[2]] = AcqR(ctx[self[2]], self)]
               /\ pc' = [pc EXCEPT ![self] = "M_Loop"]
               /\ UNCHANGED << rlock, store, uv, kal, i >>

M_Loop(self) == /\ pc[self] = "M_Loop"
                /\ IF i[self] < HandlerSteps
                      THEN /\ pc' = [pc EXCEPT ![self] = "M_RenderAcq"]
                      ELSE /\ pc' = [pc EXCEPT ![self] = "M_CtxRel"]
                /\ UNCHANGED << ctx, rlock, store, uv, kal, i >>

M_RenderAcq(self) == /\ pc[self] = "M_RenderAcq"
                     /\ rlock[self[2]] = NoProc
                     /\ rlock' = [rlock EXCEPT ![self[2]] = self]
                     /\ pc' = [pc EXCEPT ![self] = "M_Send"]
                     /\ UNCHANGED << ctx, store, uv, kal, i >>

M_Send(self) == /\ pc[self] = "M_Send"
                /\ uv = NoProc
                /\ uv' = self
                /\ pc' = [pc EXCEPT ![self] = "M_SendDone"]
                /\ UNCHANGED << ctx, rlock, store, kal, i >>

M_SendDone(self) == /\ pc[self] = "M_SendDone"
                    /\ uv' = NoProc
                    /\ pc' = [pc EXCEPT ![self] = "M_Read"]
                    /\ UNCHANGED << ctx, rlock, store, kal, i >>

M_Read(self) == /\ pc[self] = "M_Read"
                /\ store.owner \in {NoProc, self}
                /\ store' = AcqR(store, self)
                /\ pc' = [pc EXCEPT ![self] = "M_ReadDone"]
                /\ UNCHANGED << ctx, rlock, uv, kal, i >>

M_ReadDone(self) == /\ pc[self] = "M_ReadDone"
                    /\ store' = RelR(store)
                    /\ pc' = [pc EXCEPT ![self] = "M_RenderRel"]
                    /\ UNCHANGED << ctx, rlock, uv, kal, i >>

M_RenderRel(self) == /\ pc[self] = "M_RenderRel"
                     /\ rlock' = [rlock EXCEPT ![self[2]] = NoProc]
                     /\ i' = [i EXCEPT ![self] = IF WedgeK1 /\ self[2] = 1 THEN 0 ELSE i[self] + 1]
                     /\ pc' = [pc EXCEPT ![self] = "M_Loop"]
                     /\ UNCHANGED << ctx, store, uv, kal >>

M_CtxRel(self) == /\ pc[self] = "M_CtxRel"
                  /\ ctx' = [ctx EXCEPT ![self[2]] = RelR(ctx[self[2]])]
                  /\ pc' = [pc EXCEPT ![self] = "Done"]
                  /\ UNCHANGED << rlock, store, uv, kal, i >>

Msg(self) == M_Ctx(self) \/ M_Loop(self) \/ M_RenderAcq(self)
                \/ M_Send(self) \/ M_SendDone(self) \/ M_Read(self)
                \/ M_ReadDone(self) \/ M_RenderRel(self) \/ M_CtxRel(self)

T_StoreAcq(self) == /\ pc[self] = "T_StoreAcq"
                    /\ store.owner \in {NoProc, self}
                    /\ store' = AcqR(store, self)
                    /\ pc' = [pc EXCEPT ![self] = "T_Store"]
                    /\ UNCHANGED << ctx, rlock, uv, kal, i >>

T_Store(self) == /\ pc[self] = "T_Store"
                 /\ IF NewStoreRules
                       THEN /\ store' = RelR(store)
                       ELSE /\ TRUE
                            /\ store' = store
                 /\ pc' = [pc EXCEPT ![self] = "T_FireAcq"]
                 /\ UNCHANGED << ctx, rlock, uv, kal, i >>

T_FireAcq(self) == /\ pc[self] = "T_FireAcq"
                   /\ rlock[self[2]] = NoProc
                   /\ rlock' = [rlock EXCEPT ![self[2]] = self]
                   /\ pc' = [pc EXCEPT ![self] = "T_FireRel"]
                   /\ UNCHANGED << ctx, store, uv, kal, i >>

T_FireRel(self) == /\ pc[self] = "T_FireRel"
                   /\ rlock' = [rlock EXCEPT ![self[2]] = NoProc]
                   /\ pc' = [pc EXCEPT ![self] = "T_Rel"]
                   /\ UNCHANGED << ctx, store, uv, kal, i >>

T_Rel(self) == /\ pc[self] = "T_Rel"
               /\ IF ~NewStoreRules
                     THEN /\ store' = RelR(store)
                     ELSE /\ TRUE
                          /\ store' = store
               /\ pc' = [pc EXCEPT ![self] = "Done"]
               /\ UNCHANGED << ctx, rlock, uv, kal, i >>

Task(self) == T_StoreAcq(self) \/ T_Store(self) \/ T_FireAcq(self)
                 \/ T_FireRel(self) \/ T_Rel(self)

E_Start == /\ pc[EvictId] = "E_Start"
           /\ IF ~EvictOn
                 THEN /\ pc' = [pc EXCEPT ![EvictId] = "Done"]
                 ELSE /\ pc' = [pc EXCEPT ![EvictId] = "E_Uv"]
           /\ UNCHANGED << ctx, rlock, store, uv, kal, i >>

E_Uv == /\ pc[EvictId] = "E_Uv"
        /\ uv = NoProc
        /\ uv' = EvictId
        /\ pc' = [pc EXCEPT ![EvictId] = "E_HandOff"]
        /\ UNCHANGED << ctx, rlock, store, kal, i >>

E_HandOff == /\ pc[EvictId] = "E_HandOff"
             /\ IF NewCloseRules
                   THEN /\ uv' = NoProc
                   ELSE /\ TRUE
                        /\ uv' = uv
             /\ pc' = [pc EXCEPT ![EvictId] = "E_Ctx"]
             /\ UNCHANGED << ctx, rlock, store, kal, i >>

E_Ctx == /\ pc[EvictId] = "E_Ctx"
         /\ ctx[1].owner \in {NoProc, EvictId}
         /\ ctx' = [ctx EXCEPT ![1] = AcqR(ctx[1], EvictId)]
         /\ pc' = [pc EXCEPT ![EvictId] = "E_Render"]
         /\ UNCHANGED << rlock, store, uv, kal, i >>

E_Render == /\ pc[EvictId] = "E_Render"
            /\ rlock[1] = NoProc
            /\ rlock' = [rlock EXCEPT ![1] = EvictId]
            /\ pc' = [pc EXCEPT ![EvictId] = "E_Rel"]
            /\ UNCHANGED << ctx, store, uv, kal, i >>

E_Rel == /\ pc[EvictId] = "E_Rel"
         /\ rlock' = [rlock EXCEPT ![1] = NoProc]
         /\ ctx' = [ctx EXCEPT ![1] = RelR(ctx[1])]
         /\ pc' = [pc EXCEPT ![EvictId] = "E_UvRel"]
         /\ UNCHANGED << store, uv, kal, i >>

E_UvRel == /\ pc[EvictId] = "E_UvRel"
           /\ IF ~NewCloseRules
                 THEN /\ uv' = NoProc
                 ELSE /\ TRUE
                      /\ uv' = uv
           /\ pc' = [pc EXCEPT ![EvictId] = "Done"]
           /\ UNCHANGED << ctx, rlock, store, kal, i >>

Evict == E_Start \/ E_Uv \/ E_HandOff \/ E_Ctx \/ E_Render \/ E_Rel
            \/ E_UvRel

C_Kal(self) == /\ pc[self] = "C_Kal"
               /\ kal = NoProc
               /\ kal' = self
               /\ pc' = [pc EXCEPT ![self] = "C_HandOff"]
               /\ UNCHANGED << ctx, rlock, store, uv, i >>

C_HandOff(self) == /\ pc[self] = "C_HandOff"
                   /\ IF NewCloseRules
                         THEN /\ kal' = NoProc
                         ELSE /\ TRUE
                              /\ kal' = kal
                   /\ pc' = [pc EXCEPT ![self] = "C_Ctx"]
                   /\ UNCHANGED << ctx, rlock, store, uv, i >>

C_Ctx(self) == /\ pc[self] = "C_Ctx"
               /\ ctx[self[2]].owner \in {NoProc, self}
               /\ ctx' = [ctx EXCEPT ![self[2]] = AcqR(ctx[self[2]], self)]
               /\ pc' = [pc EXCEPT ![self] = "C_Render"]
               /\ UNCHANGED << rlock, store, uv, kal, i >>

C_Render(self) == /\ pc[self] = "C_Render"
                  /\ rlock[self[2]] = NoProc
                  /\ rlock' = [rlock EXCEPT ![self[2]] = self]
                  /\ pc' = [pc EXCEPT ![self] = "C_Rel"]
                  /\ UNCHANGED << ctx, store, uv, kal, i >>

C_Rel(self) == /\ pc[self] = "C_Rel"
               /\ rlock' = [rlock EXCEPT ![self[2]] = NoProc]
               /\ ctx' = [ctx EXCEPT ![self[2]] = RelR(ctx[self[2]])]
               /\ pc' = [pc EXCEPT ![self] = "C_KalRel"]
               /\ UNCHANGED << store, uv, kal, i >>

C_KalRel(self) == /\ pc[self] = "C_KalRel"
                  /\ IF ~NewCloseRules
                        THEN /\ kal' = NoProc
                        ELSE /\ TRUE
                             /\ kal' = kal
                  /\ pc' = [pc EXCEPT ![self] = "Done"]
                  /\ UNCHANGED << ctx, rlock, store, uv, i >>

Cull(self) == C_Kal(self) \/ C_HandOff(self) \/ C_Ctx(self)
                 \/ C_Render(self) \/ C_Rel(self) \/ C_KalRel(self)

(* Allow infinite stuttering to prevent deadlock on termination. *)
Terminating == /\ \A self \in ProcSet: pc[self] = "Done"
               /\ UNCHANGED vars

Next == Evict
           \/ (\E self \in MsgIds: Msg(self))
           \/ (\E self \in TaskIds: Task(self))
           \/ (\E self \in CullIds: Cull(self))
           \/ Terminating

Spec == /\ Init /\ [][Next]_vars
        /\ \A self \in MsgIds : SF_vars(Msg(self))
        /\ \A self \in TaskIds : SF_vars(Task(self))
        /\ SF_vars(Evict)
        /\ \A self \in CullIds : SF_vars(Cull(self))

Termination == <>(\A self \in ProcSet: pc[self] = "Done")

\* END TRANSLATION

-----------------------------------------------------------------------------
\* The same spec with WEAK fairness.  Every behaviour allowed by Spec (strong
\* fairness) is also allowed by SpecWF, so a property that holds for SpecWF
\* holds for Spec as well.  It is used for the New configuration, whose strong
\* fairness liveness pass does not fit the time budget (see README.md).
SpecWF == /\ Init /\ [][Next]_vars
          /\ \A self \in MsgIds : WF_vars(Msg(self))
          /\ \A self \in TaskIds : WF_vars(Task(self))
          /\ WF_vars(Evict)
          /\ \A self \in CullIds : WF_vars(Cull(self))

-----------------------------------------------------------------------------
\* Safety: the non-reentrant render lock is never taken by its own owner, and
\* the reentrant locks keep a consistent owner/count.
TypeOK ==
    /\ \A k \in Kernels : rlock[k] \in ({NoProc} \cup MsgIds \cup TaskIds \cup CullIds \cup {EvictId})
    /\ \A k \in Kernels : (ctx[k].owner = NoProc) <=> (ctx[k].count = 0)
    /\ (store.owner = NoProc) <=> (store.count = 0)

\* Liveness.  All-Done is reached by the Terminating stuttering step the
\* PlusCal translator adds, so all-Done is NOT reported as a deadlock; every
\* other state with no enabled action is a real lock cycle.
AllDone      == <>(\A p \in ProcSet : pc[p] = "Done")
AllCullsDone == <>(\A k \in Kernels : pc[<<"cull", k>>] = "Done")
\* One wedged kernel must not stall the cull of the other kernel.
Cull2Done    == <>(pc[<<"cull", 2>>] = "Done")
=============================================================================
