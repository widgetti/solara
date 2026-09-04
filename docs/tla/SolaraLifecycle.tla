------------------------- MODULE SolaraLifecycle -------------------------
(***************************************************************************)
(* The kernel lifecycle race between a cull and a reconnect.                *)
(*                                                                          *)
(* This is NOT one of the fixed deadlocks.  It is a race we suspect in       *)
(* solara/server/kernel_context.py and did not fix.                          *)
(*                                                                          *)
(* The cull decides "no connected pages" under self.lock, RELEASES the lock, *)
(* and only then calls close() (kernel_context.py:530-541, the comment there *)
(* says close() must run outside self.lock because its persistence teardown  *)
(* does backend I/O).  close() then marks the kernel CLOSING under a         *)
(* DIFFERENT lock, self._lifecycle_lock (kernel_context.py:361-365).         *)
(*                                                                          *)
(* page_connect (kernel_context.py:484-493) checks is_closing() twice, once  *)
(* outside self.lock and once inside it, and then sets the page CONNECTED.   *)
(* Because the cull's decision and the CLOSING mark are not under the same   *)
(* hold of self.lock, a reconnect can slip in between them.                  *)
(*                                                                          *)
(* page_connect also cancels the pending cull task, but that only helps      *)
(* while the cull still sleeps.  Once the cull has passed its decision, the  *)
(* close runs on its own thread and the cancel does nothing.  That is        *)
(* exactly the window modelled here, so the cancel needs no extra variable.  *)
(*                                                                          *)
(* FixLifecycle = TRUE is the candidate fix: mark CLOSING under the same     *)
(* self.lock hold as the decision.                                          *)
(***************************************************************************)
EXTENDS Naturals, TLC

CONSTANT FixLifecycle

NoProc == "none"

(*--algorithm SolaraLifecycle

variables
    ctxOwner  = NoProc,          \* context.lock (self.lock)
    lifecycle = "open",          \* _lifecycle_state: open / closing / closed
    page      = "disconnected";  \* page_status of the one page

fair+ process Cull = "cull"
begin
CU_Lock:
    await ctxOwner = NoProc;
    ctxOwner := "cull";
CU_Decide:
    \* "with self.lock: if PageStatus.CONNECTED in self.page_status.values(): return False"
    if page = "connected" then
        ctxOwner := NoProc;
        goto Done;               \* a page reconnected in time, keep the kernel
    elsif FixLifecycle then
        lifecycle := "closing";  \* CANDIDATE FIX: mark under the same lock hold
    end if;
CU_Unlock:
    ctxOwner := NoProc;          \* close() runs OUTSIDE self.lock
CU_Closing:
    lifecycle := "closing";      \* close(): under _lifecycle_lock, not self.lock
CU_Lock2:
    await ctxOwner = NoProc;
    ctxOwner := "cull";
CU_Finish:
    \* _finish_close: "for key in self.page_status: self.page_status[key] = CLOSED"
    page := "closed";
    lifecycle := "closed";
    ctxOwner := NoProc;
end process;

fair+ process Reconnect = "recon"
begin
RE_FastCheck:
    if lifecycle /= "open" then
        goto Done;               \* page_connect:485, the check outside the lock
    end if;
RE_Lock:
    await ctxOwner = NoProc;
    ctxOwner := "recon";
RE_Check:
    if lifecycle /= "open" then  \* page_connect:489, the check inside the lock
        ctxOwner := NoProc;
        goto Done;               \* RuntimeError: cannot connect to a closed kernel
    end if;
RE_Connect:
    page := "connected";         \* page_status[page_id] = CONNECTED
    ctxOwner := NoProc;
end process;

end algorithm; *)

\* BEGIN TRANSLATION
VARIABLES ctxOwner, lifecycle, page, pc

vars == << ctxOwner, lifecycle, page, pc >>

ProcSet == {"cull"} \cup {"recon"}

Init == (* Global variables *)
        /\ ctxOwner = NoProc
        /\ lifecycle = "open"
        /\ page = "disconnected"
        /\ pc = [self \in ProcSet |-> CASE self = "cull" -> "CU_Lock"
                                        [] self = "recon" -> "RE_FastCheck"]

CU_Lock == /\ pc["cull"] = "CU_Lock"
           /\ ctxOwner = NoProc
           /\ ctxOwner' = "cull"
           /\ pc' = [pc EXCEPT !["cull"] = "CU_Decide"]
           /\ UNCHANGED << lifecycle, page >>

CU_Decide == /\ pc["cull"] = "CU_Decide"
             /\ IF page = "connected"
                   THEN /\ ctxOwner' = NoProc
                        /\ pc' = [pc EXCEPT !["cull"] = "Done"]
                        /\ UNCHANGED lifecycle
                   ELSE /\ IF FixLifecycle
                              THEN /\ lifecycle' = "closing"
                              ELSE /\ TRUE
                                   /\ UNCHANGED lifecycle
                        /\ pc' = [pc EXCEPT !["cull"] = "CU_Unlock"]
                        /\ UNCHANGED ctxOwner
             /\ page' = page

CU_Unlock == /\ pc["cull"] = "CU_Unlock"
             /\ ctxOwner' = NoProc
             /\ pc' = [pc EXCEPT !["cull"] = "CU_Closing"]
             /\ UNCHANGED << lifecycle, page >>

CU_Closing == /\ pc["cull"] = "CU_Closing"
              /\ lifecycle' = "closing"
              /\ pc' = [pc EXCEPT !["cull"] = "CU_Lock2"]
              /\ UNCHANGED << ctxOwner, page >>

CU_Lock2 == /\ pc["cull"] = "CU_Lock2"
            /\ ctxOwner = NoProc
            /\ ctxOwner' = "cull"
            /\ pc' = [pc EXCEPT !["cull"] = "CU_Finish"]
            /\ UNCHANGED << lifecycle, page >>

CU_Finish == /\ pc["cull"] = "CU_Finish"
             /\ page' = "closed"
             /\ lifecycle' = "closed"
             /\ ctxOwner' = NoProc
             /\ pc' = [pc EXCEPT !["cull"] = "Done"]

Cull == CU_Lock \/ CU_Decide \/ CU_Unlock \/ CU_Closing \/ CU_Lock2
           \/ CU_Finish

RE_FastCheck == /\ pc["recon"] = "RE_FastCheck"
                /\ IF lifecycle /= "open"
                      THEN /\ pc' = [pc EXCEPT !["recon"] = "Done"]
                      ELSE /\ pc' = [pc EXCEPT !["recon"] = "RE_Lock"]
                /\ UNCHANGED << ctxOwner, lifecycle, page >>

RE_Lock == /\ pc["recon"] = "RE_Lock"
           /\ ctxOwner = NoProc
           /\ ctxOwner' = "recon"
           /\ pc' = [pc EXCEPT !["recon"] = "RE_Check"]
           /\ UNCHANGED << lifecycle, page >>

RE_Check == /\ pc["recon"] = "RE_Check"
            /\ IF lifecycle /= "open"
                  THEN /\ ctxOwner' = NoProc
                       /\ pc' = [pc EXCEPT !["recon"] = "Done"]
                  ELSE /\ pc' = [pc EXCEPT !["recon"] = "RE_Connect"]
                       /\ UNCHANGED ctxOwner
            /\ UNCHANGED << lifecycle, page >>

RE_Connect == /\ pc["recon"] = "RE_Connect"
              /\ page' = "connected"
              /\ ctxOwner' = NoProc
              /\ pc' = [pc EXCEPT !["recon"] = "Done"]
              /\ UNCHANGED lifecycle

Reconnect == RE_FastCheck \/ RE_Lock \/ RE_Check \/ RE_Connect

(* Allow infinite stuttering to prevent deadlock on termination. *)
Terminating == /\ \A self \in ProcSet: pc[self] = "Done"
               /\ UNCHANGED vars

Next == Cull \/ Reconnect
           \/ Terminating

Spec == /\ Init /\ [][Next]_vars
        /\ SF_vars(Cull)
        /\ SF_vars(Reconnect)

Termination == <>(\A self \in ProcSet: pc[self] = "Done")

\* END TRANSLATION

-----------------------------------------------------------------------------
\* A page is never CONNECTED on a kernel that is closing or closed.
NoStrandedPage == (page = "connected") => (lifecycle = "open")

AllDone == <>(\A p \in ProcSet : pc[p] = "Done")
=============================================================================
