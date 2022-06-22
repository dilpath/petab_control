# Changes
- [X] change data to 7-day average
  - [X] change observables to match
    - deaths were fitted in the original publication
      - not shown in ODEs but implemented as multiplier of recovery rate
        - [ ] implement deaths? would not be simply SIR anymore then... could add additional `-rho * Infected` to describe deaths in `Infected` ODE
	- [X] implemented like a scaling factor
  - [X] updated YAML to match

- clean up model
  - [X] remove unuseful annotations
  - [X] remove location (NY/CA) duplicates
  - [X] reimplement initial assignments as PEtab conditions
    - [X] remove `Io`, replace with `initial_Infected`
  - [X] remove `Pop` from model, replace with sum of species
  - [X] remove lockdown effects
  - [X] rewrite to use `beta` instead of `R_0` dimensionless formulation
  - [X] removed all function definitions (integrated only function into reaction kinetic law directly)
  - [X] removed compartment term multiplier from all reactions

- parameters
  - [X] renamed greek letters with `_` suffix
  - [X] only kept `gamma_` and `beta_`, removed all other parameters
  - [X] changed all model parameters (greek letters) to have `0.1` as nominal value
  - [ ] added `mortality` parameter to fit deaths similarly to original publication

- initial species parameters
  - [X] removed initial assignments
    - [X] changed `Susceptible(0) = Population - Infected(0)` to just fix `Susceptible(0) = 83000000`
  - [X] set all initial species to be estimated

- visualize table
  - [X] updated to match new observables
