# Tennessee-First Indicator Roadmap

## Phase 1 (high-confidence, low-cost, safer)

Use official/public datasets and stable APIs first.

1. Labor Market Indicators

- Tennessee Unemployment Rate (FRED: TNUR)
- Tennessee Nonfarm Employment (FRED: TNNA)
- US Initial Jobless Claims (FRED: ICSA)

2. Consumer Activity Indicators

- US CPI (FRED: CPIAUCSL)
- US Retail and Food Services Sales (FRED: RSXFS)

3. Business Activity Indicators

- US Industrial Production Index (FRED: INDPRO)

4. Housing Market Indicators

- 30-Year Mortgage Rate (FRED: MORTGAGE30US)

5. Transportation / Travel Indicators

- US Regular Gasoline Price (FRED: GASREGW)

Why this phase is strongest:

- Low cost and durable access.
- Strong legal posture and transparency.
- High reproducibility in scheduled batch runs.

## Phase 2 (useful but harder)

Activate only after licensing, reliability, and maintenance plan are clear.

- Online job postings / labor demand (partner APIs)
- Apartment rent listings (controlled scrape or licensed feed)
- Freight load postings (partner API)
- Restaurant activity proxies (mobility/reservation datasets)
- Airline demand (BTS + airport-specific sources)
- Bankruptcy filings (official court extraction pipeline)

Phase 2 gating checks:

- Terms of use are explicitly compatible.
- Historical continuity is reliable.
- Per-run compute and storage remain low-cost.
- Data revision behavior is documented.

## Avoid / Defer (risky, expensive, unstable)

- Broad uncontrolled scraping without explicit policy review.
- Commercial data feeds with volatile pricing and lock-in risk.
- Signals with no reproducible statewide baseline or unstable definitions.
- Small business closure data without robust official denominator/reference.

## Candidate evaluation from discussion

1. Online job postings: good signal, phase 2 pending licensing.
2. Apartment rent listings: useful but scrape risk and quality variance.
3. Commercial real estate listings: likely expensive/fragmented, phase 2 or defer.
4. Freight load postings: high value but often commercial and costly.
5. Restaurant activity: useful proxy, but source continuity can be weak.
6. Online retail prices: method complexity high, defer unless stable feed exists.
7. Google search intensity: potentially useful but should remain a supporting signal only.
8. Bankruptcy filings: valuable but requires robust normalization and legal workflow design.
9. Small business closures: defer until better source foundation.
10. Airline demand: feasible with official transportation datasets, phase 2.
11. Traffic intensity: potentially useful if official sensor/API access is sustainable.
