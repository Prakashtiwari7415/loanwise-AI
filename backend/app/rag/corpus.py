"""Curated, verifiable knowledge corpus for LoanWise Grounded Financial RAG."""

from __future__ import annotations

from app.rag.models import SourceDocument

CURATED_SOURCES: list[SourceDocument] = [
    SourceDocument(
        id="rbi-kfs-apr-guidelines-2024",
        title="RBI Directions on Key Fact Statement (KFS) for Retail and MSME Term Loans",
        url="https://www.rbi.org.in/Scripts/NotificationUser.aspx?Id=12658&Mode=0",
        publisher="Reserve Bank of India",
        source_type="regulatory",
        publication_date="2024-04-15",
        retrieval_date="2024-10-01",
        last_verified_date="2024-10-01",
        document_version="RBI/2024-25/11 DOR.STR.REC.13/21.04.048/2024-25",
        content="""
Reserve Bank of India (RBI) Regulatory Directions on Key Fact Statement (KFS):

1. Mandatory Provision: All Regulated Entities (REs), including commercial banks and Non-Banking Financial Companies (NBFCs), must provide a standardized Key Fact Statement (KFS) to all retail prospective borrowers (including car loan, personal loan, and home loan borrowers) before executing the loan agreement.

2. Annual Percentage Rate (APR) Disclosure: The KFS must prominently disclose the Annual Percentage Rate (APR). The APR reflects the total cost of credit to the borrower expressed as an annualized percentage of the loan amount. APR must encompass the annual interest rate plus all mandatory upfront processing fees, documentation charges, valuation fees, and mandatory insurance premiums.

3. Binding Fees and Charges Prohibition: Regulated entities cannot charge any fee, charge, or disbursement cost that is not explicitly disclosed in the Key Fact Statement. Any fee not stated in the KFS cannot be levied upon the borrower at any stage of the loan lifecycle.

4. Validity Period: The KFS must provide a validity period of at least three (3) working days for retail loans. During this period, the borrower has the right to review the offer and agree to the terms without any unilateral adverse changes by the lender.

5. Cooling-off / Look-up Period: Borrowers are entitled to an explicit cooling-off or look-up period during which they can exit the loan without incurring prepayment or foreclosure penalties, by repaying the disbursed principal and the proportionate APR accrued.
""".strip(),
    ),
    SourceDocument(
        id="rbi-foreclosure-prepayment-rules",
        title="RBI Circular on Levy of Foreclosure Charges / Pre-payment Penalty on Floating Rate Loans",
        url="https://www.rbi.org.in/Scripts/NotificationUser.aspx?Id=8913&Mode=0",
        publisher="Reserve Bank of India",
        source_type="regulatory",
        publication_date="2014-05-07",
        retrieval_date="2024-10-01",
        last_verified_date="2024-10-01",
        document_version="RBI/2013-14/582 DBOD.Dir.BC.No.107/13.03.00/2013-14",
        content="""
Reserve Bank of India (RBI) Circular on Foreclosure Charges and Prepayment Penalties:

1. Prohibition on Floating Rate Term Loans: Regulated commercial banks and NBFCs are strictly prohibited from charging foreclosure charges or pre-payment penalties on any floating rate term loans sanctioned to individual borrowers (for purposes other than business).

2. Applicability to Retail Borrowers: This zero-penalty rule applies to retail floating-rate car loans, personal loans, and home loans taken by individuals, whether with or without co-obligants.

3. Fixed Rate Loan Exception: For fixed-rate loans or loans sanctioned to corporate entities/businesses, lenders are legally permitted to levy prepayment and foreclosure charges, provided these charges are explicitly defined and quantified in the loan agreement and Key Fact Statement (KFS).

4. Partial Prepayment: Lenders cannot penalize individual borrowers who make partial prepayments toward reducing their outstanding principal balance on floating rate retail loans.
""".strip(),
    ),
    SourceDocument(
        id="rbi-fair-practices-penal-charges-2023",
        title="RBI Guidelines on Fair Practices Code – Penal Charges in Loan Accounts",
        url="https://www.rbi.org.in/Scripts/NotificationUser.aspx?Id=12527&Mode=0",
        publisher="Reserve Bank of India",
        source_type="regulatory",
        publication_date="2023-08-18",
        retrieval_date="2024-10-01",
        last_verified_date="2024-10-01",
        document_version="RBI/2023-24/53 DoR.MCS.REC.28/01.01.001/2023-24",
        content="""
Reserve Bank of India (RBI) Fair Practices Code on Penal Charges:

1. Penal Charges vs Penal Interest: Penalty for default, delayed EMI payment, or non-compliance with loan terms must be levied strictly as 'penal charges'. Lenders are prohibited from levying 'penal interest' that increases the contracted interest rate or compounds on overdue amounts.

2. No Compounding of Penal Charges: Regulated entities shall not capitalize penal charges. No interest can be computed on outstanding penal charges.

3. Reasonable and Transparent: The quantum of penal charges must be proportionate to the default and clearly disclosed in the Key Fact Statement (KFS) under a dedicated head.

4. Individual Borrower Protection: The penal charges on individual borrowers for non-business loans must not exceed the penal charges applicable to non-individual entities for similar defaults.
""".strip(),
    ),
    SourceDocument(
        id="sbi-auto-loan-fee-schedule-2024",
        title="State Bank of India: Retail Auto Loan Schedule of Fees and Benchmark Pricing",
        url="https://sbi.co.in/web/personal-banking/loans/auto-loans",
        publisher="State Bank of India",
        source_type="lender_disclosure",
        publication_date="2024-01-01",
        retrieval_date="2024-05-15",
        last_verified_date="2024-05-15",
        document_version="SBI/RET-AUTO/2024-Q1",
        content="""
State Bank of India (SBI) Auto Loan Schedule of Charges and Benchmark Terms:

1. Benchmark Rate Linkage: SBI car loan floating interest rates are pegged to the 1-Year Marginal Cost of Funds based Lending Rate (MCLR) / External Benchmark Lending Rate (EBLR). Rates are adjusted based on borrower credit score tier (CIBIL score).

2. Processing Fees: Standard processing fee is 0.25% to 0.75% of the sanctioned loan amount, subject to a minimum of Rs. 1,500 and maximum of Rs. 10,000 plus applicable GST. Special seasonal or festival campaigns may offer temporary processing fee waivers.

3. Prepayment and Foreclosure Terms: In compliance with RBI directives, SBI levies zero (0%) foreclosure penalty and zero pre-payment charges on floating rate car loans to individual borrowers. Fixed rate car loans incur up to 3% pre-payment fee if foreclosed within 24 months.

4. Freshness and Rate Volatility Notice: Lender terms and benchmark spreads are subject to periodic revision following RBI Monetary Policy Committee rate changes. Information was last verified on 2024-05-15. Borrowers must verify current interest rate cards and processing fee waiver status directly with SBI before applying.
""".strip(),
    ),
    SourceDocument(
        id="loanwise-reducing-vs-flat-rate-guide",
        title="LoanWise Education: Reducing Balance Method vs Flat Interest Rate Calculation",
        url="https://loanwise.internal/education/reducing-vs-flat-rate",
        publisher="LoanWise AI Financial Education",
        source_type="educational",
        publication_date="2024-06-01",
        retrieval_date="2024-10-01",
        last_verified_date="2024-10-01",
        document_version="EDU-2024-01",
        content="""
LoanWise Financial Education Guide on Reducing Balance vs Flat Interest Rate:

1. Reducing Balance Method (Standard for Banks): In a reducing balance (or diminishing balance) loan, interest is calculated each month only on the remaining outstanding principal. As monthly EMIs pay down principal, the monthly interest portion decreases and the principal repayment portion increases.

2. Flat Rate Method (Marketing Device): In a flat rate loan, the lender calculates interest on the entire original loan amount throughout the full tenure, completely ignoring the fact that regular monthly EMIs are reducing the principal.

3. Mathematical Comparison: A 7.5% flat interest rate is NOT cheap. For a 5-year loan, a 7.5% flat rate is mathematically equivalent to an effective reducing interest rate of approximately 13.5% to 14.0% per annum.

4. Borrower Advice: Always demand the Annual Percentage Rate (APR) or the reducing balance equivalent rate. Never compare a flat rate offer directly with a reducing balance offer without converting it.
""".strip(),
    ),
    SourceDocument(
        id="loanwise-prepayment-tenure-amortization-guide",
        title="LoanWise Education: Loan Prepayment Economics and Tenure Trade-offs",
        url="https://loanwise.internal/education/prepayment-tradeoffs",
        publisher="LoanWise AI Financial Education",
        source_type="educational",
        publication_date="2024-06-01",
        retrieval_date="2024-10-01",
        last_verified_date="2024-10-01",
        document_version="EDU-2024-02",
        content="""
LoanWise Financial Education Guide on Prepayment Economics:

1. Amortization Front-Loading: Standard reducing-balance amortization schedules are front-loaded with interest. During the initial 12 to 24 months of a 5-year car loan, the largest share of each monthly EMI goes toward interest rather than principal reduction.

2. Optimal Prepayment Window: Prepaying principal early in the loan tenure produces the highest interest savings. Making an extra payment in year 1 reduces the principal base that accrues interest across all remaining years.

3. Tenure vs Total Cost Trade-off: Extending loan tenure (e.g., from 36 months to 84 months) lowers the monthly EMI payment, improving short-term cash flow. However, it substantially increases the total borrowing cost because interest compounds over a much longer duration.

4. Verifying Prepayment Allocation: Borrowers must verify that any lump-sum prepayment is credited directly toward reducing the principal balance rather than held as advanced EMIs.
""".strip(),
    ),
]

# Include verified lender benchmark rate cards into curated knowledge corpus
from app.rag.rates import get_rate_source_documents

CURATED_SOURCES.extend(get_rate_source_documents())
