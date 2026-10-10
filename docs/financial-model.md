# Financial model

For a monthly reducing-balance loan, EMI is calculated as `P × r × (1+r)^n / ((1+r)^n − 1)`, where `r` is annual rate divided by 1200 and `n` is the number of months. Zero-interest loans use principal divided by months. Values use Python `Decimal` and are rounded to paise.

Schedules reconcile opening balance, interest, principal and closing balance each month. The final payment is adjusted to prevent a negative balance caused by rounding.

Affordability is an explainable educational heuristic. It uses selected current/proposed EMI burden and income remaining after user-provided expenses. It is explicitly not an approval prediction or universal lending rule.

Prepayment preserves the current EMI to estimate reduced tenure and interest. It deliberately excludes unknown lender penalties. Rate scenarios calculate the cost at selected rate changes rather than predicting future rates.
