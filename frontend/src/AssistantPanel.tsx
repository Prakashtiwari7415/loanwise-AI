import { FormEvent, KeyboardEvent, useEffect, useRef, useState } from "react";
import { sendAssistantMessage, type AssistantChatResponse, type BreakdownItem, type LoanContext } from "./api";

const SUGGESTED_QUESTIONS = [
  "Explain my current EMI.",
  "What are my total monthly car expenses including EMI, fuel, and insurance?",
  "What does RBI mandate about KFS cooling-off period?",
  "Are foreclosure charges allowed on floating car loans?",
  "What is the difference between flat and reducing rate?",
  "Can I save interest through prepayment?",
  "What happens if interest rates rise by 1%?",
];

const TOOL_NAMES_MAP: Record<string, string> = {
  calculate_emi: "EMI & Borrowing Cost Engine",
  calculate_affordability: "Affordability Heuristic Engine",
  compare_loans: "Loan Comparison & Recommendation",
  simulate_prepayment: "Prepayment Schedule Simulation",
  simulate_rate_change: "Rate Sensitivity Engine",
  estimate_vehicle_ownership: "Vehicle Ownership Cost Estimator",
};

type ChatMessage = {
  id: string;
  role: "user" | "assistant";
  text?: string;
  response?: AssistantChatResponse;
  timestamp: Date;
  isError?: boolean;
  canRetry?: boolean;
  failedPrompt?: string;
};

export type ExternalAssistantAction = {
  prompt: string;
  context?: LoanContext;
  timestamp: number;
};

type AssistantPanelProps = {
  loanContext: LoanContext;
  externalAction?: ExternalAssistantAction | null;
  onClearExternalAction?: () => void;
};

export function AssistantPanel({ loanContext, externalAction, onClearExternalAction }: AssistantPanelProps) {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [lastPrompt, setLastPrompt] = useState<string | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView?.({ behavior: "smooth" });
  }, [messages, loading]);

  useEffect(() => {
    if (externalAction && externalAction.prompt) {
      handleSend(externalAction.prompt, externalAction.context);
      onClearExternalAction?.();
      const el = document.getElementById("assistant-panel-section");
      if (el) {
        el.scrollIntoView?.({ behavior: "smooth" });
      }
    }
  }, [externalAction]);

  async function handleSend(promptText: string, customContext?: LoanContext) {
    const trimmed = promptText.trim();
    if (!trimmed || loading) return;

    setErrorMessage(null);
    setLastPrompt(trimmed);
    setInput("");

    const userMsgId = `user-${Date.now()}`;
    const userMsg: ChatMessage = {
      id: userMsgId,
      role: "user",
      text: trimmed,
      timestamp: new Date(),
    };

    setMessages((prev) => [...prev, userMsg]);
    setLoading(true);

    try {
      const response = await sendAssistantMessage({
        message: trimmed,
        loan_context: customContext ?? loanContext,
      });

      const assistantMsg: ChatMessage = {
        id: `asst-${Date.now()}`,
        role: "assistant",
        response,
        timestamp: new Date(),
      };
      setMessages((prev) => [...prev, assistantMsg]);
    } catch (err) {
      const detail = err instanceof Error ? err.message : "Failed to get response from assistant.";
      let userFriendlyError = detail;

      if (detail.includes("503") || detail.toLowerCase().includes("missing or invalid api key") || detail.toLowerCase().includes("not configured")) {
        userFriendlyError = "Gemini API key is not configured. Please set GEMINI_API_KEY in the backend environment.";
      } else if (detail.includes("429") || detail.toLowerCase().includes("quota") || detail.toLowerCase().includes("rate limit")) {
        userFriendlyError = "Gemini API rate limit or quota exceeded. Please check your Gemini quota or wait a moment.";
      } else if (detail.includes("504") || detail.toLowerCase().includes("timeout")) {
        userFriendlyError = "Assistant request timed out. Please retry.";
      }

      setErrorMessage(userFriendlyError);
      const errorMsg: ChatMessage = {
        id: `err-${Date.now()}`,
        role: "assistant",
        text: userFriendlyError,
        isError: true,
        canRetry: true,
        failedPrompt: trimmed,
        timestamp: new Date(),
      };
      setMessages((prev) => [...prev, errorMsg]);
    } finally {
      setLoading(false);
    }
  }

  function handleSubmit(event: FormEvent) {
    event.preventDefault();
    handleSend(input);
  }

  function handleKeyDown(event: KeyboardEvent<HTMLTextAreaElement>) {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      handleSend(input);
    }
  }

  function handleRetry(failedPrompt?: string) {
    const promptToRetry = failedPrompt || lastPrompt;
    if (promptToRetry) {
      handleSend(promptToRetry);
    }
  }

  return (
    <section id="assistant-panel-section" className="assistant-card" aria-label="LoanWise AI Assistant">
      <header className="assistant-header">
        <div className="assistant-title-group">
          <div className="assistant-badge">
            <span className="assistant-icon">✦</span>
            <h2>LoanWise AI Assistant</h2>
          </div>
          <p className="assistant-subtitle">Understand your loan. Explore better decisions.</p>
        </div>
        <div className="assistant-status-pill" aria-live="polite">
          <span className={`status-indicator ${errorMessage ? "status-warning" : loading ? "status-busy" : "status-ready"}`} />
          <small>{errorMessage ? "Attention needed" : loading ? "Calculating…" : "Ready"}</small>
        </div>
      </header>

      {/* Suggested Questions */}
      <div className="assistant-suggestions" aria-label="Suggested questions">
        <p className="suggestions-label">Explore common scenarios:</p>
        <div className="suggestions-list">
          {SUGGESTED_QUESTIONS.map((question) => (
            <button
              key={question}
              type="button"
              className="suggestion-pill"
              onClick={() => handleSend(question)}
              disabled={loading}
            >
              {question}
            </button>
          ))}
        </div>
      </div>

      {/* Chat Messages */}
      <div className="assistant-messages" tabIndex={0} role="region" aria-label="Message history">
        {messages.length === 0 && (
          <div className="assistant-empty-state">
            <div className="empty-sparkle">💬</div>
            <h3>Ask anything about your loan</h3>
            <p>
              The assistant uses your active loan details and LoanWise's deterministic financial engine to calculate
              EMIs, test prepayment savings, and evaluate rate risks.
            </p>
          </div>
        )}

        {messages.map((msg) => (
          <div key={msg.id} className={`assistant-bubble-row ${msg.role === "user" ? "user-row" : "bot-row"}`}>
            {msg.role === "user" ? (
              <div className="user-bubble">
                <p>{msg.text}</p>
              </div>
            ) : msg.isError ? (
              <div className="bot-bubble error-bubble" role="alert">
                <div className="error-header">
                  <span>⚠️</span>
                  <strong>Unable to complete calculation</strong>
                </div>
                <p className="error-body">{msg.text}</p>
                {msg.canRetry && (
                  <button
                    type="button"
                    className="retry-button"
                    onClick={() => handleRetry(msg.failedPrompt)}
                    disabled={loading}
                  >
                    ↻ Retry Question
                  </button>
                )}
              </div>
            ) : msg.response ? (
              <div className="bot-bubble structured-response">
                {/* Headline */}
                <div className="response-headline-box">
                  <h4 className="response-headline">{msg.response.headline}</h4>
                  {msg.response.needs_more_information && (
                    <span className="needs-info-badge">Requires More Information</span>
                  )}
                </div>

                {/* Tool calls badge */}
                {msg.response.tool_calls_used.length > 0 && (
                  <div className="tool-usage-row">
                    {msg.response.tool_calls_used.map((tool) => (
                      <span key={tool} className="tool-badge">
                        ⚙ Used financial tool: <b>{TOOL_NAMES_MAP[tool] ?? tool}</b>
                      </span>
                    ))}
                  </div>
                )}

                {/* Estimate notice */}
                {msg.response.is_estimate && (
                  <div className="estimate-notice" role="note">
                    <span className="estimate-icon">≈</span>
                    <span>This response contains estimated values. Assumed components are marked below.</span>
                  </div>
                )}

                {/* Cost breakdown table */}
                {msg.response.breakdown && msg.response.breakdown.length > 0 && (
                  <div className="breakdown-table-wrap" aria-label="Cost breakdown">
                    <table className="breakdown-table">
                      <caption className="breakdown-caption">Monthly Cost Breakdown</caption>
                      <thead>
                        <tr>
                          <th scope="col">Component</th>
                          <th scope="col" className="amount-col">Low (₹)</th>
                          <th scope="col" className="amount-col">High (₹)</th>
                          <th scope="col">Type</th>
                        </tr>
                      </thead>
                      <tbody>
                        {msg.response.breakdown.map((item: BreakdownItem, idx: number) => (
                          <tr
                            key={idx}
                            className={item.is_estimate ? "breakdown-row estimated-row" : "breakdown-row"}
                            title={item.assumption ?? undefined}
                          >
                            <td className="breakdown-label">
                              {item.label}
                              {item.is_estimate && <span className="estimated-badge">≈ Estimated</span>}
                            </td>
                            <td className="breakdown-amount">{item.amount_low}</td>
                            <td className="breakdown-amount">
                              {item.amount_high === item.amount_low ? "—" : item.amount_high}
                            </td>
                            <td className="breakdown-category">{item.category ?? "—"}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}

                {/* Detailed message */}
                <div className="response-message">
                  {msg.response.message.split("\n\n").map((para, i) => (
                    <p key={i}>{para}</p>
                  ))}
                </div>

                {/* Advantages and Risks */}
                {(msg.response.advantages.length > 0 || msg.response.risks.length > 0) && (
                  <div className="response-factors">
                    {msg.response.advantages.length > 0 && (
                      <div className="factor-block advantages-block">
                        <h5>Key Advantages</h5>
                        <ul>
                          {msg.response.advantages.map((adv, idx) => (
                            <li key={idx}>✓ {adv}</li>
                          ))}
                        </ul>
                      </div>
                    )}
                    {msg.response.risks.length > 0 && (
                      <div className="factor-block risks-block">
                        <h5>Watch Out / Risks</h5>
                        <ul>
                          {msg.response.risks.map((risk, idx) => (
                            <li key={idx}>⚠ {risk}</li>
                          ))}
                        </ul>
                      </div>
                    )}
                  </div>
                )}

                {/* Recommended Action */}
                {msg.response.recommended_action && (
                  <div className="recommended-action-box">
                    <span className="action-tag">Recommended Action</span>
                    <p>{msg.response.recommended_action}</p>
                  </div>
                )}

                {/* Verified Sources and Citations */}
                {msg.response.sources && msg.response.sources.length > 0 && (
                  <div className="citations-box" aria-label="Verified Source References">
                    <div className="citations-header">
                      <span className="citations-icon">📚</span>
                      <h5>Verified Regulatory & Research Sources</h5>
                    </div>
                    <div className="citations-list">
                      {msg.response.sources.map((src, sIdx) => {
                        const typeBadgeClass =
                          src.source_type === "regulatory"
                            ? "source-badge-regulatory"
                            : src.source_type === "lender_disclosure"
                            ? "source-badge-lender"
                            : "source-badge-educational";
                        const typeLabel =
                          src.source_type === "regulatory"
                            ? "Regulatory Mandate"
                            : src.source_type === "lender_disclosure"
                            ? "Lender Disclosure"
                            : "Financial Guide";

                        return (
                          <article key={sIdx} className="citation-card">
                            <div className="citation-top">
                              <div className="citation-title-row">
                                {src.url ? (
                                  <a
                                    href={src.url}
                                    target="_blank"
                                    rel="noopener noreferrer"
                                    className="citation-link"
                                    title="Open official source (opens in new tab)"
                                  >
                                    {src.title} <span className="external-arrow">↗</span>
                                  </a>
                                ) : (
                                  <strong className="citation-title">{src.title}</strong>
                                )}
                              </div>
                              <div className="citation-meta-tags">
                                <span className={`source-type-pill ${typeBadgeClass}`}>
                                  {typeLabel}
                                </span>
                                <span className="publisher-tag">{src.publisher}</span>
                                {src.verified_date && (
                                  <span className="date-tag">Verified: {src.verified_date}</span>
                                )}
                              </div>
                            </div>

                            {src.is_potentially_stale && (
                              <div className="stale-warning-banner" role="alert">
                                <span>⚠️ Notice:</span> Lender terms change frequently. Verification date is older than 90 days. Confirm current terms directly with lender.
                              </div>
                            )}

                            {src.excerpt && (
                              <p className="citation-excerpt">
                                "{src.excerpt}"
                              </p>
                            )}
                          </article>
                        );
                      })}
                    </div>
                  </div>
                )}

                {/* Assumptions Footnote */}
                {msg.response.assumptions.length > 0 && (
                  <div className="assumptions-footnote">
                    <small>
                      <b>Assumptions:</b> {msg.response.assumptions.join(" • ")}
                    </small>
                  </div>
                )}
              </div>
            ) : (
              <div className="bot-bubble">
                <p>{msg.text}</p>
              </div>
            )}
          </div>
        ))}

        {loading && (
          <div className="assistant-bubble-row bot-row">
            <div className="bot-bubble loading-bubble" role="status" aria-label="Calculating">
              <span className="typing-dot" />
              <span className="typing-dot" />
              <span className="typing-dot" />
              <small>Consulting financial engine…</small>
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Input Form */}
      <form className="assistant-input-form" onSubmit={handleSubmit}>
        <div className="input-row">
          <textarea
            ref={textareaRef}
            className="assistant-textarea"
            placeholder="Ask about EMI, interest sensitivity, prepayment savings, or affordability…"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            rows={2}
            disabled={loading}
            aria-label="Ask LoanWise AI Assistant"
          />
          <button
            type="submit"
            className="assistant-send-button"
            disabled={loading || !input.trim()}
            aria-label="Send message"
          >
            {loading ? "…" : "Send ↑"}
          </button>
        </div>
        <div className="assistant-input-footer">
          <small>Press Enter to send, Shift + Enter for new line. Backed by deterministic financial tools.</small>
        </div>
      </form>
    </section>
  );
}
