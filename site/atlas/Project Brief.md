# Atlas — Project Brief

**Size:** full · **Written:** 2026-09-14 · **Last revised:** 2026-10-26 · **Serves:** Grow self-service revenue

> **To** rebuild the customer portal's sign-up **so that** new customers can open an account on their own, in one sitting.

## Why

Opening an account today takes an email to support, a form, and a call back: four days on average, and a third of the people who start never finish. Support spends a day a week on it. Sign-up is the first thing a customer does with us, and it is the slowest.

## Outcome and done-when

New customers open an account on their own, in one sitting.

Done when (specific and checkable, three to five):

1. A new customer can sign up, verify their email and reach their dashboard without contacting support.
2. Median time from start to a working account is under ten minutes.
3. Support's sign-up tickets fall by three quarters.
4. The old form is switched off.

Key deliverables: the WBS's Key Deliverable rows (`wbs.py deliverables`).

**Stop if:** the payments provider cannot verify identity inside the flow, so a call back stays necessary.

### Measures

| ID | Measure | Role | Kind | C/A | Baseline | From | Target | By | How measured | Every | Current | As of | Source | WBS |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| M1 | Sign-ups completed without support | lag | H | C | 0% | 2026-09-14 | 90% | 2027-01-31 | Completed sign-ups with no support ticket attached, over all completed sign-ups | sprint | 0% | 2026-10-26 | measured | |
| M2 | Median minutes to a working account | lag | N | C | 5760 | 2026-09-14 | 10 | 2027-01-31 | Median, start of the form to first dashboard load, from the portal's events | sprint | 5760 | 2026-10-26 | measured | |
| M3 | Sign-up steps live in test | lead | N | C | 0 | 2026-09-14 | 5 | 2026-12-15 | Steps of the new flow passing their acceptance criteria in test | sprint | 2 | 2026-10-26 | measured | |

## Appetite and budget

- **Appetite:** four sprints of the team's capacity, about two thirds of each. When the work doesn't fit, the scope is cut.
- **Budget:** none beyond the team.

## Scope

- **In:** the sign-up flow, email verification, identity check through the payments provider, the welcome to the dashboard.
- **Out:** business accounts with several users; migrating existing customers.
- **Assumptions and constraints:** the payments provider's identity check is available in its sandbox by the second sprint.

## Approach

Two-week sprints with a WBS, a RAID and a team board; the sponsor receives a status report at each close-out.

## Who it is for

New customers, and the support team who answer them. See the Stakeholder Register.
