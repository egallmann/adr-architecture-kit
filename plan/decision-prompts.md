# Decision Prompts

1. Must all in-process consumers use `ArchitectureRepository` once it exists?
2. Is `NormalizedArchitectureModel` versioned independently from compiled
   registry schemas, or only alongside them?
3. Which provenance fields are mandatory for every normalized entity,
   relationship, and unresolved record?
4. What unresolved record shape is guaranteed stable before kernel 1.0?
5. When is raw bundle access acceptable, and for which caller classes?
6. How are bare local IDs and future qualified IDs separated semantically?
7. What compatibility promise does the repository boundary make before the
   kernel contract reaches 1.0?
8. Should the additive architecture graph eventually be projected from the
   normalized model boundary instead of directly from registry records?

