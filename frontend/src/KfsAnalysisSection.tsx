import { FormEvent, useEffect, useMemo, useRef, useState } from "react";
import {
  calculateLoan,
  uploadAndAnalyzeDocument,
  type DocumentAnalysisResponse,
  type DocumentField,
  type LoanContext,
  type LoanSummary,
} from "./api";

const inr = (value: string | number) =>
  new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency: "INR",
    maximumFractionDigits: 0,
  }).format(Number(value));

export function parseNumberFromText(text: string | null | undefined): number | null {
  if (!text) return null;
  const stripped = text.replace(/(?:rs\.?|₹|inr)\s*/gi, "");
  const match = stripped.match(/([\d,]+(?:\.\d+)?)/);
  if (!match) return null;
  const numStr = match[1].replace(/,/g, "");
  const num = parseFloat(numStr);
  return isNaN(num) ? null : num;
}

export function parseTenureMonths(text: string | null | undefined): number | null {
  if (!text) return null;
  const yearMatch = text.match(/(\d+)\s*(?:years?|yrs?)/i);
  if (yearMatch) {
    return parseInt(yearMatch[1], 10) * 12;
  }
  const monthMatch = text.match(/(\d+)\s*(?:months?|m)?/i);
  if (monthMatch) {
    return parseInt(monthMatch[1], 10);
  }
  return null;
}

const MAX_FILE_BYTES = 8 * 1024 * 1024; // 8 MB

type ActivePlan = {
  loanAmount: number;
  interestRate: number;
  tenure: number;
  emi: string;
  total_interest: string;
  total_borrowing_cost: string;
};

type KfsAnalysisSectionProps = {
  activePlan?: ActivePlan | null;
  onAskAssistant?: (prompt: string, context?: LoanContext) => void;
};

export function KfsAnalysisSection({ activePlan, onAskAssistant }: KfsAnalysisSectionProps) {
  const [file, setFile] = useState<File | null>(null);
  const [isDragging, setIsDragging] = useState(false);
  const [analyzing, setAnalyzing] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [analysisResult, setAnalysisResult] = useState<DocumentAnalysisResponse | null>(null);

  // User manual supplies for missing or overridden fields
  const [manualRate, setManualRate] = useState<string>("");
  const [manualTenure, setManualTenure] = useState<string>("");
  const [manualAmount, setManualAmount] = useState<string>("");

  // Deterministic calculation state
  const [calculatedKfsLoan, setCalculatedKfsLoan] = useState<LoanSummary | null>(null);
  const [calcLoading, setCalcLoading] = useState(false);
  const [calcError, setCalcError] = useState<string | null>(null);

  const fileInputRef = useRef<HTMLInputElement>(null);

  function handleFileSelect(selectedFile: File | null) {
    if (!selectedFile) return;
    setUploadError(null);

    const isPdf =
      selectedFile.type === "application/pdf" ||
      selectedFile.name.toLowerCase().endsWith(".pdf");

    if (!isPdf) {
      setUploadError("Only PDF documents are supported. Please select a valid KFS PDF.");
      return;
    }

    if (selectedFile.size > MAX_FILE_BYTES) {
      setUploadError("Document exceeds the 8 MB limit. Please select a smaller PDF.");
      return;
    }

    setFile(selectedFile);
    setAnalysisResult(null);
    setCalculatedKfsLoan(null);
    setManualRate("");
    setManualTenure("");
    setManualAmount("");
  }

  function handleDrop(event: React.DragEvent<HTMLDivElement>) {
    event.preventDefault();
    setIsDragging(false);
    if (event.dataTransfer.files && event.dataTransfer.files.length > 0) {
      handleFileSelect(event.dataTransfer.files[0]);
    }
  }

  function handleDragOver(event: React.DragEvent<HTMLDivElement>) {
    event.preventDefault();
    setIsDragging(true);
  }

  function handleDragLeave(event: React.DragEvent<HTMLDivElement>) {
    event.preventDefault();
    setIsDragging(false);
  }

  function handleRemoveFile() {
    setFile(null);
    setAnalysisResult(null);
    setCalculatedKfsLoan(null);
    setUploadError(null);
    setCalcError(null);
    if (fileInputRef.current) {
      fileInputRef.current.value = "";
    }
  }

  async function handleAnalyze() {
    if (!file || analyzing) return;
    setAnalyzing(true);
    setUploadError(null);

    try {
      const result = await uploadAndAnalyzeDocument(file);
      setAnalysisResult(result);
    } catch (err) {
      setUploadError(err instanceof Error ? err.message : "Failed to analyze document.");
    } finally {
      setAnalyzing(false);
    }
  }

  // Parse fields from extraction
  const extracted = useMemo(() => {
    if (!analysisResult) return null;
    const fields = analysisResult.extracted_fields;

    const rawAmount = fields.loan_amount?.value;
    const rawRate = fields.interest_rate?.value;
    const rawTenure = fields.tenure?.value;
    const rawFee = fields.processing_fee?.value;
    const rawCharges = fields.other_charges?.value;

    return {
      lender: fields.lender?.value ?? null,
      lenderConf: fields.lender?.confidence ?? "not_found",

      loanAmountStr: rawAmount ?? null,
      loanAmountNum: parseNumberFromText(rawAmount),
      loanAmountConf: fields.loan_amount?.confidence ?? "not_found",

      interestRateStr: rawRate ?? null,
      interestRateNum: parseNumberFromText(rawRate),
      interestRateConf: fields.interest_rate?.confidence ?? "not_found",

      tenureStr: rawTenure ?? null,
      tenureNum: parseTenureMonths(rawTenure),
      tenureConf: fields.tenure?.confidence ?? "not_found",

      emiStr: fields.emi?.value ?? null,
      emiConf: fields.emi?.confidence ?? "not_found",

      processingFeeStr: rawFee ?? null,
      processingFeeNum: parseNumberFromText(rawFee) ?? 0,
      processingFeeConf: fields.processing_fee?.confidence ?? "not_found",

      otherChargesStr: rawCharges ?? null,
      otherChargesNum: parseNumberFromText(rawCharges) ?? 0,
      otherChargesConf: fields.other_charges?.confidence ?? "not_found",

      aprStr: fields.apr?.value ?? null,
      aprConf: fields.apr?.confidence ?? "not_found",

      rateTypeStr: fields.rate_type?.value ?? null,
      rateTypeConf: fields.rate_type?.confidence ?? "not_found",

      prepaymentTermsStr: fields.prepayment_terms?.value ?? null,
      prepaymentTermsConf: fields.prepayment_terms?.confidence ?? "not_found",

      foreclosureTermsStr: fields.foreclosure_terms?.value ?? null,
      foreclosureTermsConf: fields.foreclosure_terms?.confidence ?? "not_found",
    };
  }, [analysisResult]);

  // Effective values considering manual inputs
  const effectiveInputs = useMemo(() => {
    if (!extracted) return null;
    const amt = manualAmount ? parseFloat(manualAmount) : extracted.loanAmountNum;
    const rate = manualRate ? parseFloat(manualRate) : extracted.interestRateNum;
    const tenure = manualTenure ? parseInt(manualTenure, 10) : extracted.tenureNum;

    const isComplete = Boolean(amt && amt > 0 && rate && rate > 0 && tenure && tenure >= 12);

    return {
      loanAmount: amt ?? null,
      interestRate: rate ?? null,
      tenureMonths: tenure ?? null,
      processingFee: extracted.processingFeeNum,
      otherCharges: extracted.otherChargesNum,
      isComplete,
      missingFields: [
        ...(!amt || amt <= 0 ? ["Loan Amount"] : []),
        ...(!rate || rate <= 0 ? ["Interest Rate"] : []),
        ...(!tenure || tenure < 12 ? ["Tenure (at least 12 months)"] : []),
      ],
    };
  }, [extracted, manualAmount, manualRate, manualTenure]);

  // Trigger deterministic calculation when complete
  useEffect(() => {
    if (!effectiveInputs || !effectiveInputs.isComplete) {
      setCalculatedKfsLoan(null);
      return;
    }

    let isMounted = true;
    async function runCalc() {
      setCalcLoading(true);
      setCalcError(null);
      try {
        const res = await calculateLoan({
          loan_amount: effectiveInputs!.loanAmount!,
          annual_interest_rate: effectiveInputs!.interestRate!,
          tenure_months: effectiveInputs!.tenureMonths!,
          processing_fee: effectiveInputs!.processingFee,
          other_charges: effectiveInputs!.otherCharges,
        });
        if (isMounted) {
          setCalculatedKfsLoan(res);
        }
      } catch (err) {
        if (isMounted) {
          setCalcError(err instanceof Error ? err.message : "Calculation failed.");
        }
      } finally {
        if (isMounted) {
          setCalcLoading(false);
        }
      }
    }

    runCalc();
    return () => {
      isMounted = false;
    };
  }, [effectiveInputs]);

  // Assistant prompt triggers
  function triggerAssistant(questionType: "explain" | "charges" | "verify" | "compare") {
    if (!onAskAssistant || !extracted || !effectiveInputs) return;

    const lender = extracted.lender || "the lender";
    const amt = effectiveInputs.loanAmount || extracted.loanAmountNum || 0;
    const rate = effectiveInputs.interestRate || extracted.interestRateNum || 0;
    const tenure = effectiveInputs.tenureMonths || extracted.tenureNum || 0;

    const context: LoanContext = {
      loan_amount: amt > 0 ? amt : undefined,
      annual_interest_rate: rate > 0 ? rate : undefined,
      tenure_months: tenure > 0 ? tenure : undefined,
      processing_fee: effectiveInputs.processingFee >= 0 ? effectiveInputs.processingFee : undefined,
      other_charges: effectiveInputs.otherCharges >= 0 ? effectiveInputs.otherCharges : undefined,
    };

    let prompt = "";
    if (questionType === "explain") {
      prompt = `Explain this Key Fact Statement (KFS) in simple language. Lender: ${lender}, Loan Amount: ₹${amt}, Interest Rate: ${rate}%, Tenure: ${tenure} months. What is the total borrowing cost and what are the main conditions?`;
    } else if (questionType === "charges") {
      prompt = `Explain the fee structure in this KFS document: Processing fee of ₹${effectiveInputs.processingFee} and other charges of ₹${effectiveInputs.otherCharges}. Are there hidden charges or upfront deductions I should look out for?`;
    } else if (questionType === "verify") {
      prompt = `Based on this KFS offer (${extracted.rateTypeStr || "disclosed"} rate, prepayment terms: ${extracted.prepaymentTermsStr || "not specified"}, foreclosure: ${extracted.foreclosureTermsStr || "not specified"}), what specific questions and clauses should I verify with ${lender} before signing?`;
    } else if (questionType === "compare") {
      if (activePlan) {
        prompt = `Compare this KFS offer (${lender}: ₹${amt} at ${rate}% for ${tenure} months, EMI ₹${calculatedKfsLoan?.emi ?? extracted.emiStr ?? "unknown"}) against my current plan (₹${activePlan.loanAmount} at ${activePlan.interestRate}% for ${activePlan.tenure} months, EMI ${activePlan.emi}). Which option is financially sounder and why?`;
      } else {
        prompt = `How does this KFS offer (${lender}: ₹${amt} at ${rate}% for ${tenure} months) compare with standard market auto loan terms?`;
      }
    }

    onAskAssistant(prompt, context);
  }

  function formatConfidence(conf: string): { label: string; className: string } {
    switch (conf) {
      case "high":
        return { label: "High confidence", className: "badge-high" };
      case "medium":
        return { label: "Medium", className: "badge-medium" };
      case "needs_review":
        return { label: "Needs review", className: "badge-review" };
      case "not_found":
      default:
        return { label: "Not found in document", className: "badge-not-found" };
    }
  }

  function renderFieldRow(label: string, value: string | null, confidence: string) {
    const conf = formatConfidence(confidence);
    const displayValue = value ? value : "Not found in document";
    const isFound = confidence !== "not_found" && Boolean(value);

    return (
      <div className="kfs-field-row" key={label}>
        <span className="kfs-field-label">{label}</span>
        <span className={`kfs-field-value ${isFound ? "value-found" : "value-missing"}`}>
          {displayValue}
        </span>
        <span className={`kfs-badge ${conf.className}`} title={`Extraction status: ${confidence}`}>
          {conf.label}
        </span>
      </div>
    );
  }

  // Comparisons with active plan
  const planDelta = useMemo(() => {
    if (!activePlan || !calculatedKfsLoan) return null;
    const currentEmi = parseFloat(activePlan.emi);
    const kfsEmi = parseFloat(calculatedKfsLoan.emi);
    const emiDiff = kfsEmi - currentEmi;

    const currentTotalCost = parseFloat(activePlan.total_borrowing_cost);
    const kfsTotalCost = parseFloat(calculatedKfsLoan.total_borrowing_cost);
    const costDiff = kfsTotalCost - currentTotalCost;

    return {
      emiDiff,
      costDiff,
      isKfsCheaper: costDiff < 0,
    };
  }, [activePlan, calculatedKfsLoan]);

  return (
    <section className="kfs-section" aria-label="Key Fact Statement Document Intelligence">
      <header className="kfs-header">
        <div className="section-heading">
          <p className="eyebrow">02 / KEY FACT STATEMENT (KFS) INTELLIGENCE</p>
          <h2>Upload & verify loan document</h2>
        </div>
        <p className="kfs-intro">
          Upload a Key Fact Statement or loan sanction letter (PDF) to extract terms with conservative
          extraction and verify financial estimates through our deterministic calculation engine.
        </p>
      </header>

      {/* Upload Box */}
      <div
        className={`kfs-dropzone ${isDragging ? "dropzone-active" : ""} ${file ? "has-file" : ""}`}
        onDrop={handleDrop}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onClick={() => !file && fileInputRef.current?.click()}
        role="region"
        aria-label="PDF file upload area"
      >
        <input
          ref={fileInputRef}
          type="file"
          accept=".pdf,application/pdf"
          style={{ display: "none" }}
          onChange={(e) => handleFileSelect(e.target.files ? e.target.files[0] : null)}
          aria-label="Upload KFS PDF document"
        />

        {!file ? (
          <div className="dropzone-content">
            <div className="dropzone-icon">📄</div>
            <p className="dropzone-title">
              <strong>Click to upload</strong> or drag & drop your KFS PDF
            </p>
            <p className="dropzone-hint">Standard RBI-mandated KFS or sanction letter (PDF, max 8 MB)</p>
          </div>
        ) : (
          <div className="file-info-box">
            <div className="file-meta">
              <span className="file-icon">📑</span>
              <div>
                <strong className="file-name">{file.name}</strong>
                <span className="file-size">{(file.size / 1024).toFixed(1)} KB</span>
              </div>
            </div>
            <div className="file-actions">
              <button
                type="button"
                className="button-secondary"
                onClick={(e) => {
                  e.stopPropagation();
                  handleRemoveFile();
                }}
                disabled={analyzing}
                aria-label="Remove uploaded file"
              >
                Remove
              </button>
              <button
                type="button"
                className="button-primary"
                onClick={(e) => {
                  e.stopPropagation();
                  handleAnalyze();
                }}
                disabled={analyzing}
                aria-label="Analyze KFS document"
              >
                {analyzing ? "Extracting terms…" : "Analyze document →"}
              </button>
            </div>
          </div>
        )}
      </div>

      {/* Upload / Extraction Errors */}
      {uploadError && (
        <div className="kfs-error-alert" role="alert">
          <span className="error-icon">⚠️</span>
          <div className="error-text">
            <strong>Unable to analyze document</strong>
            <p>{uploadError}</p>
          </div>
          <button type="button" className="retry-btn" onClick={handleAnalyze} disabled={analyzing}>
            Retry
          </button>
        </div>
      )}

      {/* Loading Feedback */}
      {analyzing && (
        <div className="kfs-loading-bar" aria-live="polite">
          <div className="loading-spinner" />
          <span>Parsing PDF pages and extracting loan terms with PyMuPDF…</span>
        </div>
      )}

      {/* Extraction Results */}
      {analysisResult && extracted && (
        <div className="kfs-results-container">
          <div className="kfs-card terms-card">
            <div className="card-header">
              <div>
                <span className="pill-tag">DOCUMENT EXTRACTED</span>
                <h3>Extracted Loan Terms</h3>
              </div>
              <span className="filename-chip">{analysisResult.filename}</span>
            </div>

            <p className="kfs-disclaimer">{analysisResult.disclaimer}</p>

            <div className="kfs-fields-grid">
              {renderFieldRow("Lender Name", extracted.lender, extracted.lenderConf)}
              {renderFieldRow("Sanctioned Amount", extracted.loanAmountStr, extracted.loanAmountConf)}
              {renderFieldRow("Interest Rate", extracted.interestRateStr, extracted.interestRateConf)}
              {renderFieldRow("Interest Rate Type", extracted.rateTypeStr, extracted.rateTypeConf)}
              {renderFieldRow("Loan Tenure", extracted.tenureStr, extracted.tenureConf)}
              {renderFieldRow("Monthly EMI (Disclosed)", extracted.emiStr, extracted.emiConf)}
              {renderFieldRow("Processing Fee", extracted.processingFeeStr, extracted.processingFeeConf)}
              {renderFieldRow("Other Charges", extracted.otherChargesStr, extracted.otherChargesConf)}
              {renderFieldRow("Annual Percentage Rate (APR)", extracted.aprStr, extracted.aprConf)}
              {renderFieldRow("Prepayment Terms", extracted.prepaymentTermsStr, extracted.prepaymentTermsConf)}
              {renderFieldRow("Foreclosure Terms", extracted.foreclosureTermsStr, extracted.foreclosureTermsConf)}
            </div>

            <div className="kfs-warnings-list">
              {analysisResult.warnings.map((w, idx) => (
                <small key={idx} className="warning-item">
                  ℹ {w}
                </small>
              ))}
            </div>
          </div>

          {/* Missing Inputs Form if incomplete */}
          {effectiveInputs && !effectiveInputs.isComplete && (
            <div className="kfs-card missing-inputs-card">
              <div className="card-header">
                <div>
                  <span className="pill-tag pill-amber">REQUIRED INPUTS NEEDED</span>
                  <h3>Supply Missing Terms</h3>
                </div>
              </div>
              <p className="missing-hint">
                The document is missing: <strong>{effectiveInputs.missingFields.join(", ")}</strong>. Provide
                them below to enable authoritative financial calculation:
              </p>
              <div className="missing-inputs-grid">
                {(!extracted.loanAmountNum || extracted.loanAmountNum <= 0) && (
                  <label className="missing-field">
                    <span>Loan Amount (₹)</span>
                    <input
                      type="number"
                      placeholder="e.g. 500000"
                      value={manualAmount}
                      onChange={(e) => setManualAmount(e.target.value)}
                      aria-label="Manual Loan Amount"
                    />
                  </label>
                )}
                {(!extracted.interestRateNum || extracted.interestRateNum <= 0) && (
                  <label className="missing-field">
                    <span>Interest Rate (%)</span>
                    <input
                      type="number"
                      step="0.05"
                      placeholder="e.g. 8.75"
                      value={manualRate}
                      onChange={(e) => setManualRate(e.target.value)}
                      aria-label="Manual Interest Rate"
                    />
                  </label>
                )}
                {(!extracted.tenureNum || extracted.tenureNum < 12) && (
                  <label className="missing-field">
                    <span>Tenure (Months, min 12)</span>
                    <input
                      type="number"
                      placeholder="e.g. 60"
                      value={manualTenure}
                      onChange={(e) => setManualTenure(e.target.value)}
                      aria-label="Manual Tenure Months"
                    />
                  </label>
                )}
              </div>
            </div>
          )}

          {/* Deterministic Financial Calculations */}
          {calculatedKfsLoan && (
            <div className="kfs-card calc-card">
              <div className="card-header">
                <div>
                  <span className="pill-tag pill-lime">FINANCIAL ENGINE VERIFIED</span>
                  <h3>LoanWise Deterministic Calculation</h3>
                </div>
                <small className="estimate-badge">* Amortization Estimate</small>
              </div>

              <div className="kfs-metrics-row">
                <article className="metric-box">
                  <span>ESTIMATED EMI</span>
                  <strong>{inr(calculatedKfsLoan.emi)}</strong>
                </article>
                <article className="metric-box">
                  <span>TOTAL INTEREST</span>
                  <strong>{inr(calculatedKfsLoan.total_interest)}</strong>
                </article>
                <article className="metric-box">
                  <span>DISCLOSED FEES</span>
                  <strong>
                    {inr(effectiveInputs ? effectiveInputs.processingFee + effectiveInputs.otherCharges : 0)}
                  </strong>
                </article>
                <article className="metric-box highlight-metric">
                  <span>TOTAL BORROWING COST</span>
                  <strong>{inr(calculatedKfsLoan.total_borrowing_cost)}</strong>
                </article>
              </div>

              <small className="calc-disclaimer">
                Calculated using LoanWise deterministic financial engine. Does not include undisclosed lender
                penalties or non-standard compounding cycles.
              </small>

              {/* Comparison with Active Plan */}
              {planDelta && activePlan && (
                <div className="plan-comparison-box">
                  <h4>Comparison with Your Current Plan</h4>
                  <div className="comparison-columns">
                    <div className="comparison-col">
                      <span className="col-label">Your Current Plan</span>
                      <p>EMI: <b>{inr(activePlan.emi)}</b></p>
                      <p>Total Cost: <b>{inr(activePlan.total_borrowing_cost)}</b></p>
                    </div>
                    <div className="comparison-col">
                      <span className="col-label">KFS Document Offer</span>
                      <p>EMI: <b>{inr(calculatedKfsLoan.emi)}</b></p>
                      <p>Total Cost: <b>{inr(calculatedKfsLoan.total_borrowing_cost)}</b></p>
                    </div>
                    <div className="comparison-delta-col">
                      <span className="col-label">Net Difference</span>
                      <p className={`delta-tag ${planDelta.isKfsCheaper ? "delta-savings" : "delta-cost"}`}>
                        {planDelta.isKfsCheaper
                          ? `Saves ${inr(Math.abs(planDelta.costDiff))} overall`
                          : `Costs ${inr(planDelta.costDiff)} more overall`}
                      </p>
                      <small>
                        Monthly EMI difference:{" "}
                        {planDelta.emiDiff > 0 ? `+${inr(planDelta.emiDiff)}` : inr(planDelta.emiDiff)}
                      </small>
                    </div>
                  </div>
                </div>
              )}
            </div>
          )}

          {/* Assistant Action Buttons */}
          <div className="kfs-assistant-actions">
            <div className="actions-header">
              <span className="assistant-sparkle">✦</span>
              <strong>Ask Assistant about this document:</strong>
            </div>
            <div className="actions-buttons-row">
              <button
                type="button"
                className="kfs-action-pill"
                onClick={() => triggerAssistant("explain")}
              >
                Explain this KFS in simple language ↗
              </button>
              <button
                type="button"
                className="kfs-action-pill"
                onClick={() => triggerAssistant("charges")}
              >
                Explain these charges ↗
              </button>
              <button
                type="button"
                className="kfs-action-pill"
                onClick={() => triggerAssistant("verify")}
              >
                What should I verify with the lender? ↗
              </button>
              <button
                type="button"
                className="kfs-action-pill"
                onClick={() => triggerAssistant("compare")}
              >
                Compare this offer with my current loan ↗
              </button>
            </div>
          </div>
        </div>
      )}
    </section>
  );
}
