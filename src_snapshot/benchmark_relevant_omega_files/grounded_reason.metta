; grounded_reason: the Stage 10 LLM-facing formal-reasoning skill
; (Cognitive Run V18). Replaces raw `metta` (blocked by
; robot_capability_profile.metta) as the LLM's only path to NAL/PLN.
;
; The LLM supplies only premise_refs (naming already-admitted machine
; claims) and an operator name -- never a raw MeTTa expression, never a
; raw (stv f c) value. grounded_reason.py resolves refs server-side
; against the real Chroma collections, runs them through the Stage 8
; grounded_proposition admission gate, and constructs the actual metta
; code itself; this equation evaluates that server-constructed code via
; the SAME native sread/eval/swrite primitives the (now-blocked) `metta`
; skill used to wrap -- confirmed this round that blocking `metta`'s own
; equation does not touch these lower-level primitives at all.

!(import! &self (library OmegaClaw-Core ./plugins/grounded_reason/grounded_reason.py))

(= (loadOmegaClawPlugin)
    (progn
        (log INFO "grounded-reason-plugin" "Registering grounded_reason Stage 10 advisory skill")
        (add-skill
            grounded_reason
            "Formal (NAL/PLN) reasoning over TWO already-recorded machine claims you already have premise_refs for (e.g. from query_mission_history's own output, a persistent-goal query, or query_observation_claims's own output -- ANY skill that returns a premise_ref may supply one) -- NEVER invent a premise_ref. ONE argument: a single-line JSON object string with EXACTLY these three keys: premise_ref_1 (string), premise_ref_2 (string), operator (string). Example: {\"premise_ref_1\":\"obs:abc123\",\"premise_ref_2\":\"obs:def456\",\"operator\":\"revision\"}. No other keys are accepted and no free-text/space-separated form is accepted -- always emit exactly this JSON shape, nothing else. operator must be exactly \"revision\" -- this is the ONLY operator this production skill accepts; any other value (e.g. deduction, pln_forward, pln_abduction) is rejected outright with a typed error, never attempted, regardless of the premises supplied. Additionally, revision itself is only accepted when both premise_refs resolve to WORLD_EVENT claims sharing the exact same subject, predicate, and predicate_aspect (see the same-thing-vs-different-thing guidance below) AND the two claims' own recorded values genuinely DISAGREE (one true, one false) -- this production skill is scoped specifically to resolving a genuine conflict between two claims about the exact same thing; a matching-shape pair whose values already AGREE is rejected outright with a typed error (that case has no real conflict for this tool to resolve). Any other pairing (different subject/predicate/predicate_aspect, a non-WORLD_EVENT claim, or a not-genuinely-opposing value pair) is rejected outright with a typed error before any reasoning is attempted. Returns a derived hypothesis with its own confidence, PLUS an explicit `advisory` field -- a JSON object with `frequency` (float), `confidence` (float), `epistemic_interpretation` (string), `recommended_cognitive_action` (string), and `authority` (always \"NONE\") -- this `advisory` field is the AUTHORITATIVE, machine-computed reading of the result: `frequency` and `confidence` are two SEPARATE, DIFFERENT numbers -- do not swap them, and do not describe a high `confidence` value as \"low confidence\" merely because `frequency` is near 0.5 (frequency near 0.5 with high confidence means the evidence is confidently, genuinely CONTRADICTORY, not that the result is uncertain). Always defer to `epistemic_interpretation`/`recommended_cognitive_action` for what this result means and what to do about it -- do not re-derive your own interpretation of the raw numbers. This is ALWAYS an advisory semantic/policy hypothesis, NEVER a claim about current physical reality; it carries no authority over what is physically true right now. If a premise_ref is not a real recorded claim, or is not eligible (e.g. a not-yet-verified or unsupported kind), you get an explicit error, never a fabricated result. IMPORTANT -- two different conflict shapes, do not treat them the same way: `revision` IS the right tool when two claims describe the EXACT SAME thing (same subject and same status/predicate/claim_kind) but disagree in VALUE -- e.g. two observation or world-event claims that the SAME predicate for the SAME subject is both true and false; this is precisely what this tool exists to combine, and neither claim's own recency or observed_at alone is a substitute for calling it -- this project's own admission contract carries no notion that a newer claim supersedes an older one, so do not silently prefer one side by which is more recent. (Two claims that AGREE about the same thing, e.g. two independent observations that the SAME mission succeeded, are mathematically a valid `revision` input too, but this particular production skill does not currently accept that agreeing-value case -- it is scoped to resolving genuine value conflicts specifically.) `revision` does NOT, by contrast, reconcile two claims that disagree about DIFFERENT predicates for the same subject (e.g. one claim says a reminder was satisfied, another says it was canceled) -- for THAT different kind of conflict you will get an empty or an unrelated/uninterpretable result, never a resolved answer, so decide conflicts like that yourself (e.g. by which claim is more recent or more directly sourced) rather than calling this tool."
            (json))))

(= (grounded_reason $json)
   (let $resolved (py-call (grounded_reason.grounded_reason_resolve_json $json))
        (if (== (first_char $resolved) "(")
            (let $result (let $code (sread $resolved) (repr (swrite (eval $code))))
                 (let $advisory (py-call (grounded_reason.materialize_advisory $result))
                      (if (== (first_char $advisory) "{")
                          (GroundedReasonResult $result (advisory $advisory) (input $json) (authority NONE))
                          (Error UNKNOWN_SKILL_CALL $advisory))))
            (Error UNKNOWN_SKILL_CALL $resolved))))
