import { FormEvent, KeyboardEvent, useEffect, useRef, useState } from "react";
import { sendAssistantMessage, type AssistantChatResponse, type LoanContext } from "./api";

const SUGGESTED_QUESTIONS = [
  "Explain my current EMI.",
  "What if I increase my down payment by ₹1 lakh?",
  "What happens if interest rates rise by 1%?",
  "Can I save interest through prepayment?",
  "Why might this loan be risky?",
];

const TOOL_NAMES_MAP: Record<string, string> = {
  calculate_emi: "EMI & Borrowing Cost Engine",
  calculate_affordability: "Affordability Heuristic Engine",
  compare_loans: "Loan Comparison & Recommendation",
  simulate_prepayment: "Prepayment Schedule Simulation",
  simulate_rate_change: "Rate Sensitivity Engine",
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

type AssistantPanelProps = {
  loanContext: LoanContext;
};

export function AssistantPanel({ loanContext }: AssistantPanelProps) {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [lastPrompt, setLastPrompt] = useState<string | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  async function handleSend(promptText: string) {
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
        loan_context: loanContext,
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
    <section className="assistant-card" aria-label="LoanWise AI Assistant">
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
