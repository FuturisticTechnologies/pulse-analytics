"""Analytical models that go beyond what SQL expresses cleanly.

The division of labour across this repository is deliberate:

* **SQL** (``database/``) owns aggregation, joins and every business
  *definition*. If two people could disagree about what a number means, it is
  defined once, in SQL, and everything reads that.
* **Python** (here) owns *modelling*: k-means, survival-style churn scoring,
  time-series forecasting, market-basket affinity, inventory optimisation.
  These need iteration, linear algebra or optimisation that SQL either cannot
  express or expresses unreadably.

Every model in this package is implemented on numpy/pandas alone - no
scikit-learn, no statsmodels. That is a deliberate constraint: it keeps the
container small, makes the maths auditable by a reviewer, and demonstrates the
algorithms rather than a call to ``.fit()``.
"""
