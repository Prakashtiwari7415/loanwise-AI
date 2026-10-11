import React, { FormEvent, useEffect, useMemo, useRef, useState } from "react";
import {
  calculateLoan,
  uploadAndAnalyzeDocument,
  type DocumentAnalysisResponse,
  type DocumentField,
  type LoanContext,
  type LoanSummary,
} from "./api";
import { KFS_TERMS_DICTIONARY, type TermExplanation } from "./types/kfsTerms";

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
  onCompareWithPlan?: (kfsLoan: LoanSummary) => void;
};

export function KfsAnalysisSection({
  activePlan,
  onAskAssistant,
  onCompareWithPlan,
}: KfsAnalysisSectionProps) {
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

  // UI tabs & view toggles
  const [showTechnicalDetails, setShowTechnicalDetails] = useState(false);
  const [selectedTermForModal, setSelectedTermForModal] = useState<TermExplanation | null>(null);
  const [showLenderQuestions, setShowLenderQuestions] = useState(false);
  const [findingsTab, setFindingsTab] = useState<"all" | "understand" | "check" | "missing" | "verify">("all");

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
    setShowLenderQuestions(false);
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
    setShowLenderQuestions(false);
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
      lenderPage: fields.lender?.page_number ?? 1,

      loanAmountStr: rawAmount ?? null,
      loanAmountNum: parseNumberFromText(rawAmount),
      loanAmountConf: fields.loan_amount?.confidence ?? "not_found",
      loanAmountPage: fields.loan_amount?.page_number ?? 1,

      interestRateStr: rawRate ?? null,
      interestRateNum: parseNumberFromText(rawRate),
      interestRateConf: fields.interest_rate?.confidence ?? "not_found",
      interestRatePage: fields.interest_rate?.page_number ?? 1,

      tenureStr: rawTenure ?? null,
      tenureNum: parseTenureMonths(rawTenure),
      tenureConf: fields.tenure?.confidence ?? "not_found",
      tenurePage: fields.tenure?.page_number ?? 1,

      emiStr: fields.emi?.value ?? null,
      emiConf: fields.emi?.confidence ?? "not_found",
      emiPage: fields.emi?.page_number ?? 1,

      processingFeeStr: rawFee ?? null,
      processingFeeNum: parseNumberFromText(rawFee) ?? 0,
      processingFeeConf: fields.processing_fee?.confidence ?? "not_found",
      processingFeePage: fields.processing_fee?.page_number ?? 1,

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
  function triggerAssistant(questionType: "explain" | "charges" | "verify" | "compare" | "questions") {
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
        prompt = `How does this KFS offer (${lender}: ₹${amt} at ${rate}% for ${tenure} months) compare with standard market terms?`;
      }
    } else if (questionType === "questions") {
      prompt = `Prepare a specific list of 5 questions I should ask the loan manager at ${lender} regarding this KFS (Sanctioned: ₹${amt}, Rate: ${rate}%, Prepayment: ${extracted.prepaymentTermsStr || "unclear"}, APR: ${extracted.aprStr || "missing"}).`;
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

  // Generate structured findings
  const findings = useMemo(() => {
    if (!extracted) return [];
    const list: {
      category: "understand" | "check" | "missing" | "verify";
      title: string;
      desc: string;
      termKey?: string;
    }[] = [];

    // Understand items
    if (extracted.rateTypeStr) {
      const isFloating = extracted.rateTypeStr.toLowerCase().includes("floating");
      list.push({
        category: "understand",
        title: `Interest Structure: ${extracted.rateTypeStr}`,
        desc: isFloating
          ? "This is a floating-rate loan. Your monthly EMI or total tenure can adjust whenever the lender's benchmark (like RBI Repo Rate) moves."
          : "This is a fixed-rate loan. Your interest rate and installment remain constant throughout the loan tenure.",
        termKey: "rate_type",
      });
    }

    if (extracted.aprStr) {
      list.push({
        category: "understand",
        title: `Disclosed APR: ${extracted.aprStr}`,
        desc: "Annual Percentage Rate includes the interest rate and mandatory bank fees. Compare APR across banks rather than just the nominal rate.",
        termKey: "apr",
      });
    }

    // Check items
    if (extracted.processingFeeStr) {
      list.push({
        category: "check",
        title: `Processing Fee: ${extracted.processingFeeStr}`,
        desc: "Check if this fee is deducted upfront from your disbursement or billed separately. Verify whether 18% GST is included.",
        termKey: "processing_fee",
      });
    }

    if (extracted.foreclosureTermsStr) {
      list.push({
        category: "check",
        title: `Foreclosure / Prepayment: ${extracted.foreclosureTermsStr}`,
        desc: "RBI mandates zero foreclosure charges for individual borrowers on floating rate loans. Check for lock-in periods or terms.",
        termKey: "prepayment_foreclosure",
      });
    }

    // Missing items
    if (!extracted.aprStr) {
      list.push({
        category: "missing",
        title: "Missing APR (Annual Percentage Rate)",
        desc: "The document does not explicitly state the APR. Request your loan officer to provide the total APR including all charges.",
        termKey: "apr",
      });
    }

    if (!extracted.prepaymentTermsStr && !extracted.foreclosureTermsStr) {
      list.push({
        category: "missing",
        title: "Prepayment / Foreclosure Terms Not Stated",
        desc: "The document does not specify prepayment terms. Clarify with the lender whether partial prepayments are permitted without penalty.",
        termKey: "prepayment_foreclosure",
      });
    }

    // Needs verification items
    if (extracted.interestRateConf === "needs_review") {
      list.push({
        category: "verify",
        title: "Interest Rate Needs Manual Verification",
        desc: "The interest rate had low extraction confidence. Cross-check Page 1 of your PDF to ensure the correct rate is entered.",
        termKey: "interest_rate",
      });
    }

    if (extracted.loanAmountConf === "needs_review") {
      list.push({
        category: "verify",
        title: "Sanctioned Amount Needs Verification",
        desc: "The loan amount was extracted with low confidence. Verify the exact figure on your sanction letter.",
        termKey: "loan_amount",
      });
    }

    return list;
  }, [extracted]);

  const filteredFindings = useMemo(() => {
    if (findingsTab === "all") return findings;
    return findings.filter((f) => f.category === findingsTab);
  }, [findings, findingsTab]);

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
              <strong>Click to upload</strong> or tap to select your KFS PDF
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
          {/* FEATURE 2.A: PLAIN-LANGUAGE OVERVIEW */}
          <div className="plain-overview-card" aria-label="Plain-language loan summary">
            <div className="card-header">
              <div>
                <span className="pill-tag pill-lime">PLAIN-LANGUAGE OVERVIEW</span>
                <h3>What this document means for you</h3>
              </div>
              <span className="source-doc-badge">Source: {analysisResult.filename}</span>
            </div>

            <p className="plain-overview-intro">
              Here is your loan broken down into simple, transparent numbers before looking at technical legal clauses.
            </p>

            <div className="plain-overview-grid">
              {/* 1. Amount you are borrowing */}
              <div className="plain-item">
                <span className="plain-item-tag tag-extracted">EXTRACTED VALUE</span>
                <h4>Amount you are borrowing</h4>
                <p className="plain-val">
                  Principal: {extracted.loanAmountStr ? extracted.loanAmountStr : "Not found in document"}
                </p>
                <small className="plain-desc">Principal sanctioned (Page {extracted.loanAmountPage || 1})</small>
              </div>

              {/* 2. Interest rate */}
              <div className="plain-item">
                <span className="plain-item-tag tag-extracted">EXTRACTED VALUE</span>
                <h4>Interest rate</h4>
                <p className="plain-val">
                  Rate: {extracted.interestRateStr
                    ? `${extracted.interestRateStr} (${extracted.rateTypeStr || "Rate type not specified"})`
                    : "Not found in document"}
                </p>
                <small className="plain-desc">Annual reducing balance rate</small>
              </div>

              {/* 3. Estimated monthly EMI */}
              <div className="plain-item">
                <span className="plain-item-tag tag-calculated">CALCULATED ESTIMATE</span>
                <h4>Estimated monthly EMI</h4>
                <p className="plain-val">
                  {calculatedKfsLoan ? inr(calculatedKfsLoan.emi) : (extracted.emiStr || "Needs terms to calculate")}
                </p>
                <small className="plain-desc">Verified by LoanWise financial engine</small>
              </div>

              {/* 4. Total repayment */}
              <div className="plain-item">
                <span className="plain-item-tag tag-calculated">CALCULATED ESTIMATE</span>
                <h4>Total repayment</h4>
                <p className="plain-val">
                  {calculatedKfsLoan ? inr(calculatedKfsLoan.total_repayment) : "Calculated when terms available"}
                </p>
                <small className="plain-desc">Principal + Total Interest over tenure</small>
              </div>

              {/* 5. Additional charges */}
              <div className="plain-item">
                <span className="plain-item-tag tag-extracted">EXTRACTED CHARGES</span>
                <h4>Additional charges disclosed</h4>
                <p className="plain-val">
                  {extracted.processingFeeStr || extracted.otherChargesStr
                    ? `Processing fee: ${extracted.processingFeeStr || "None"} ${
                        extracted.otherChargesStr ? `| Other: ${extracted.otherChargesStr}` : ""
                      }`
                    : "None disclosed in document"}
                </p>
                <small className="plain-desc">Upfront fees typically deducted from loan</small>
              </div>

              {/* 6. Things to review */}
              <div className="plain-item plain-item-review">
                <span className="plain-item-tag tag-review">KEY ITEMS TO REVIEW</span>
                <h4>Important things to check</h4>
                <p className="plain-val-sm">
                  {extracted.aprStr ? `Disclosed APR: ${extracted.aprStr}. ` : "APR is missing. "}
                  {extracted.rateTypeStr?.toLowerCase().includes("floating")
                    ? "Floating rate: rate can increase if RBI repo moves. "
                    : ""}
                  {extracted.foreclosureTermsStr
                    ? `Foreclosure: ${extracted.foreclosureTermsStr}`
                    : "Foreclosure terms not found."}
                </p>
              </div>
            </div>
          </div>

          {/* FEATURE 2.C: HIGHLIGHT IMPORTANT FINDINGS */}
          <div className="kfs-card findings-card">
            <div className="card-header">
              <div>
                <span className="pill-tag pill-navy">FINDINGS & OBSERVATIONS</span>
                <h3>Document Findings & Checkpoints</h3>
              </div>
              <div className="findings-tabs" role="tablist" aria-label="Findings filter tabs">
                <button
                  type="button"
                  className={`findings-tab-btn ${findingsTab === "all" ? "tab-active" : ""}`}
                  onClick={() => setFindingsTab("all")}
                >
                  All ({findings.length})
                </button>
                <button
                  type="button"
                  className={`findings-tab-btn ${findingsTab === "understand" ? "tab-active" : ""}`}
                  onClick={() => setFindingsTab("understand")}
                >
                  Understand this
                </button>
                <button
                  type="button"
                  className={`findings-tab-btn ${findingsTab === "check" ? "tab-active" : ""}`}
                  onClick={() => setFindingsTab("check")}
                >
                  Check this
                </button>
                <button
                  type="button"
                  className={`findings-tab-btn ${findingsTab === "missing" ? "tab-active" : ""}`}
                  onClick={() => setFindingsTab("missing")}
                >
                  Missing info
                </button>
                <button
                  type="button"
                  className={`findings-tab-btn ${findingsTab === "verify" ? "tab-active" : ""}`}
                  onClick={() => setFindingsTab("verify")}
                >
                  Needs verification
                </button>
              </div>
            </div>

            <div className="findings-grid">
              {filteredFindings.map((finding, idx) => (
                <div key={idx} className={`finding-item finding-${finding.category}`}>
                  <div className="finding-header">
                    <span className={`finding-category-pill pill-${finding.category}`}>
                      {finding.category === "understand" && "Understand this"}
                      {finding.category === "check" && "Check this"}
                      {finding.category === "missing" && "Missing information"}
                      {finding.category === "verify" && "Needs verification"}
                    </span>
                    <h4>{finding.title}</h4>
                  </div>
                  <p className="finding-desc">{finding.desc}</p>
                  {finding.termKey && KFS_TERMS_DICTIONARY[finding.termKey] && (
                    <button
                      type="button"
                      className="finding-explain-btn"
                      onClick={() => setSelectedTermForModal(KFS_TERMS_DICTIONARY[finding.termKey!])}
                    >
                      Explain this term in plain English →
                    </button>
                  )}
                </div>
              ))}
            </div>

            <small className="ethical-safety-disclaimer">
              ℹ LoanWise provides decision support and financial education. We do not declare lenders or
              loans as fraudulent or bad based on document extraction. Review findings with your lender.
            </small>
          </div>

          {/* FEATURE 2.B: EXPLAIN EVERY IMPORTANT TERM (INTERACTIVE GLOSSARY) */}
          <div className="kfs-card glossary-card">
            <div className="card-header">
              <div>
                <span className="pill-tag pill-indigo">BEGINNER'S GLOSSARY</span>
                <h3>Explain Every Important Term in Your Loan</h3>
              </div>
              <p className="glossary-subtext">
                Click any term below to see: <b>What it means</b>, <b>Why it matters</b>, and{" "}
                <b>What to check</b>.
              </p>
            </div>

            <div className="glossary-chips-row">
              {Object.values(KFS_TERMS_DICTIONARY).map((termItem) => (
                <button
                  key={termItem.id}
                  type="button"
                  className={`glossary-chip ${
                    selectedTermForModal?.id === termItem.id ? "glossary-chip-active" : ""
                  }`}
                  onClick={() => setSelectedTermForModal(termItem)}
                >
                  {termItem.term}
                </button>
              ))}
            </div>

            {selectedTermForModal && (
              <div className="term-explanation-detail" aria-live="polite">
                <div className="term-detail-header">
                  <h4>{selectedTermForModal.term}</h4>
                  <button
                    type="button"
                    className="close-term-btn"
                    onClick={() => setSelectedTermForModal(null)}
                    aria-label="Close term explanation"
                  >
                    ✕
                  </button>
                </div>

                <div className="term-three-pillars">
                  <div className="pillar-box pillar-means">
                    <span className="pillar-label">1. WHAT IT MEANS</span>
                    <p>{selectedTermForModal.whatItMeans}</p>
                  </div>
                  <div className="pillar-box pillar-matters">
                    <span className="pillar-label">2. WHY IT MATTERS</span>
                    <p>{selectedTermForModal.whyItMatters}</p>
                  </div>
                  <div className="pillar-box pillar-check">
                    <span className="pillar-label">3. WHAT TO CHECK / ASK</span>
                    <p>{selectedTermForModal.whatToCheck}</p>
                  </div>
                </div>
              </div>
            )}
          </div>

          {/* FEATURE 2.D: NEXT ACTIONS BAR */}
          <div className="kfs-next-actions-card">
            <div className="actions-header">
              <span className="assistant-sparkle">✦</span>
              <strong>Recommended Next Actions for this Document:</strong>
            </div>

            <div className="actions-buttons-row">
              {calculatedKfsLoan && onCompareWithPlan ? (
                <button
                  type="button"
                  className="kfs-action-pill pill-primary"
                  onClick={() => onCompareWithPlan(calculatedKfsLoan)}
                >
                  📊 Compare this offer
                </button>
              ) : (
                <button
                  type="button"
                  className="kfs-action-pill pill-primary"
                  onClick={() => triggerAssistant("compare")}
                >
                  📊 Compare this offer
                </button>
              )}

              <button
                type="button"
                className="kfs-action-pill"
                onClick={() => setSelectedTermForModal(KFS_TERMS_DICTIONARY.apr)}
              >
                📖 Explain a term
              </button>

              <button
                type="button"
                className="kfs-action-pill"
                onClick={() => setShowTechnicalDetails(!showTechnicalDetails)}
              >
                {showTechnicalDetails ? "Hide technical charges" : "🔍 Show all charges & raw fields"}
              </button>

              <button
                type="button"
                className="kfs-action-pill pill-highlight"
                onClick={() => setShowLenderQuestions(!showLenderQuestions)}
              >
                ❓ Help me prepare questions for the lender
              </button>

              <button
                type="button"
                className="kfs-action-pill pill-secondary"
                onClick={handleRemoveFile}
              >
                🔄 Review another document
              </button>
            </div>

            {/* Questions to Ask Lender Drawer */}
            {showLenderQuestions && (
              <div className="lender-questions-box" aria-live="polite">
                <div className="lender-q-header">
                  <h4>5 Critical Questions to Ask Your Loan Officer Before Signing</h4>
                  <button
                    type="button"
                    className="close-term-btn"
                    onClick={() => setShowLenderQuestions(false)}
                  >
                    ✕
                  </button>
                </div>
                <p className="lender-q-intro">
                  Take this checklist to your bank branch or loan executive to protect yourself against hidden costs:
                </p>
                <ol className="lender-questions-list">
                  <li>
                    <strong>Rate Type & Calculation:</strong> Is this interest rate ({extracted.interestRateStr || "quoted"}) calculated on a monthly reducing balance or a flat rate?
                  </li>
                  <li>
                    <strong>Benchmark & Reset:</strong> If this is a floating rate, which external benchmark (e.g., RBI Repo Rate / EBLR) is it tied to, and how frequently does the EMI/tenure reset?
                  </li>
                  <li>
                    <strong>Prepayment & Foreclosure Charges:</strong> Can I prepay partially or fully without penalties? (Under RBI guidelines, individual borrowers with floating rate loans cannot be charged foreclosure fees).
                  </li>
                  <li>
                    <strong>Upfront Deductions:</strong> Exactly what charges ({extracted.processingFeeStr || "processing fee"}, documentation, stamp duty, credit insurance) will be deducted from the disbursement amount before it reaches my account?
                  </li>
                  <li>
                    <strong>Cooling-off Period:</strong> What is my cooling-off period (look-up period) if I decide to cancel this sanction, and what is the exact return procedure?
                  </li>
                </ol>
                <button
                  type="button"
                  className="ask-asst-questions-btn"
                  onClick={() => triggerAssistant("questions")}
                >
                  Ask AI Assistant to customize these questions for {extracted.lender || "my lender"} ↗
                </button>
              </div>
            )}
          </div>

          {/* Technical Extracted Loan Terms Card (Expandable / Always preserves test selectors) */}
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
                      inputMode="decimal"
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
                      inputMode="decimal"
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
                      inputMode="numeric"
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
                      <p>
                        EMI: <b>{inr(activePlan.emi)}</b>
                      </p>
                      <p>
                        Total Cost: <b>{inr(activePlan.total_borrowing_cost)}</b>
                      </p>
                    </div>
                    <div className="comparison-col">
                      <span className="col-label">KFS Document Offer</span>
                      <p>
                        EMI: <b>{inr(calculatedKfsLoan.emi)}</b>
                      </p>
                      <p>
                        Total Cost: <b>{inr(calculatedKfsLoan.total_borrowing_cost)}</b>
                      </p>
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

          {/* Assistant Action Buttons (Preserved for tests & assistant flow) */}
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
