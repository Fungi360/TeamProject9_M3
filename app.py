"""Dependency-free browser front end for the existing CatalogIQ agent."""

# Basic local-host front end for manually entering and submitting agent questions.

import asyncio
import os
import re
from html import escape
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs

from vendor_catalog_agent import ask_agent


PAGE = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>CatalogIQ</title>
  <style>
    :root {
      color-scheme: light;
      --ink: #16213a;
      --muted: #65718a;
      --line: #dce2ec;
      --panel: #ffffff;
      --accent: #0b6b57;
      --accent-hover: #075643;
      --page: #edf1f6;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      min-height: 100vh;
      background:
        linear-gradient(135deg, rgba(11, 107, 87, 0.08), transparent 38%),
        var(--page);
      color: var(--ink);
      font-family: Georgia, "Times New Roman", serif;
    }
    main {
      width: min(860px, calc(100% - 32px));
      margin: 0 auto;
      padding: 52px 0;
    }
    header { margin-bottom: 24px; }
    h1 {
      margin: 0;
      font-size: clamp(2.25rem, 7vw, 4.25rem);
      line-height: 0.95;
      letter-spacing: 0;
    }
    .subtitle {
      max-width: 600px;
      margin: 14px 0 0;
      color: var(--muted);
      font-family: Arial, sans-serif;
      line-height: 1.5;
    }
    .getting-started {
      margin: 20px 0;
      border-left: 4px solid var(--accent);
      padding: 12px 16px;
      background: rgba(255, 255, 255, 0.75);
      font: 0.92rem/1.5 Arial, sans-serif;
    }
    .getting-started strong { display: block; margin-bottom: 4px; }
    form, .answer {
      border: 1px solid var(--line);
      border-radius: 8px;
      background: var(--panel);
      box-shadow: 0 16px 48px rgba(22, 33, 58, 0.08);
    }
    form { padding: 20px; }
    label {
      display: block;
      margin-bottom: 8px;
      font-family: Arial, sans-serif;
      font-weight: 700;
      font-size: 0.9rem;
    }
    textarea {
      width: 100%;
      min-height: 110px;
      resize: vertical;
      border: 1px solid #bdc6d5;
      border-radius: 6px;
      padding: 14px;
      color: var(--ink);
      background: #fbfcfe;
      font: 1.05rem/1.5 Arial, sans-serif;
    }
    textarea:focus {
      outline: 3px solid rgba(11, 107, 87, 0.16);
      border-color: var(--accent);
    }
    .actions {
      display: flex;
      align-items: center;
      gap: 12px;
      margin-top: 14px;
    }
    button {
      border: 0;
      border-radius: 6px;
      padding: 12px 18px;
      background: var(--accent);
      color: white;
      font: 700 0.95rem Arial, sans-serif;
      cursor: pointer;
    }
    button:hover { background: var(--accent-hover); }
    button:focus-visible { outline: 3px solid rgba(11, 107, 87, 0.25); }
    button:disabled {
      background: #5d786f;
      cursor: wait;
      opacity: 0.88;
    }
    .spinner {
      display: none;
      width: 16px;
      height: 16px;
      border: 2px solid rgba(255, 255, 255, 0.55);
      border-top-color: white;
      border-radius: 50%;
      animation: spin 0.8s linear infinite;
    }
    button:disabled .spinner { display: inline-block; }
    .button-content {
      display: inline-flex;
      align-items: center;
      justify-content: center;
      gap: 8px;
    }
    .loading-message {
      display: none;
      color: var(--accent);
      font: 700 0.86rem Arial, sans-serif;
    }
    .loading-message.is-visible { display: inline; }
    @keyframes spin { to { transform: rotate(360deg); } }
    .examples {
      color: var(--muted);
      font: 0.82rem/1.4 Arial, sans-serif;
    }
    .suggestions {
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
      margin-top: 12px;
    }
    .suggestion {
      border: 1px solid var(--line);
      border-radius: 999px;
      padding: 8px 12px;
      background: #f7f9fc;
      color: var(--ink);
      font: 0.82rem Arial, sans-serif;
      cursor: pointer;
    }
    .suggestion:hover { border-color: var(--accent); color: var(--accent); }
    .suggestion:focus-visible { outline: 3px solid rgba(11, 107, 87, 0.25); }
    .form-help {
      margin: 0 0 8px;
      color: var(--muted);
      font: 0.84rem/1.45 Arial, sans-serif;
    }
    .data-note {
      margin: 14px 0 0;
      color: var(--muted);
      font: 0.8rem/1.45 Arial, sans-serif;
    }
    .error {
      margin: 16px 0 0;
      border-left: 4px solid #bd3545;
      padding: 10px 12px;
      color: #861d29;
      background: #fff1f3;
      font-family: Arial, sans-serif;
    }
    .answer {
      margin-top: 20px;
      padding: 24px;
    }
    .answer h2 {
      margin: 0 0 14px;
      font: 700 1.15rem Arial, sans-serif;
    }
    .answer-content {
      overflow-wrap: anywhere;
      font: 0.96rem/1.62 Arial, sans-serif;
    }
    .answer-content > :first-child { margin-top: 0; }
    .answer-content > :last-child { margin-bottom: 0; }
    .answer-content h1,
    .answer-content h2,
    .answer-content h3 {
      margin: 22px 0 10px;
      color: var(--ink);
      font-family: Arial, sans-serif;
      line-height: 1.3;
    }
    .answer-content h1 { font-size: 1.35rem; }
    .answer-content h2 { font-size: 1.2rem; }
    .answer-content h3 { font-size: 1.05rem; }
    .answer-content p { margin: 0 0 14px; }
    .answer-content ul,
    .answer-content ol { margin: 0 0 16px; padding-left: 24px; }
    .answer-content li { margin: 5px 0; }
    .answer-content code {
      border-radius: 4px;
      padding: 2px 5px;
      background: #f0f3f7;
      font: 0.9em Consolas, monospace;
    }
    .comparison-list {
      display: grid;
      gap: 10px;
      margin: 12px 0 20px;
    }
    .comparison-card {
      border: 1px solid var(--line);
      border-left: 4px solid var(--accent);
      border-radius: 6px;
      padding: 14px 16px;
      background: #fff;
    }
    .answer-content .comparison-card h3 {
      margin: 0 0 9px;
      font-size: 1rem;
      overflow-wrap: anywhere;
    }
    .comparison-card h3 span {
      color: var(--muted);
      font-size: 0.82rem;
      font-weight: 400;
    }
    .comparison-card dl {
      margin: 0;
    }
    .comparison-card dl div {
      padding: 7px 0;
      border-top: 1px solid #edf0f4;
    }
    .comparison-card dt {
      color: var(--muted);
      font-size: 0.82rem;
      font-weight: 700;
      margin-bottom: 2px;
    }
    .comparison-card dd {
      margin: 0;
      overflow-wrap: anywhere;
    }
    .answer-content hr {
      margin: 18px 0;
      border: 0;
      border-top: 1px solid var(--line);
    }
    @media (max-width: 560px) {
      main { width: min(100% - 20px, 860px); padding: 28px 0; }
      .actions { align-items: stretch; flex-direction: column; }
      button { width: 100%; }
    }
  </style>
</head>
<body>
  <main>
    <header>
      <h1>CatalogIQ</h1>
      <p class="subtitle">Get a simple side-by-side comparison of sample products by price, quality, and material.</p>
    </header>
    <aside class="getting-started">
      <strong>New here? Start with a sample question.</strong>
      Choose one of the suggestions below, or type the product you want to compare and what matters to you.
      CatalogIQ uses sample catalog data and gives advice only; it cannot place orders.
    </aside>
    <form method="post" action="/">
      <label for="question">What would you like to compare?</label>
      <p id="question-help" class="form-help">For example, ask which option costs less or which has the highest quality.</p>
      <textarea id="question" name="question" maxlength="1000" required aria-describedby="question-help" placeholder="Compare holiday string lights across the vendors.">{question}</textarea>
      <div class="actions">
        <button id="ask-button" type="submit">
          <span class="button-content"><span class="spinner" aria-hidden="true"></span><span id="button-label">Ask CatalogIQ</span></span>
        </button>
        <span id="loading-message" class="loading-message" role="status" aria-live="polite">CatalogIQ is comparing vendor data...</span>
        <span class="examples">Available sample categories: lights, restaurant gloves, and brake pads.</span>
      </div>
      <div class="suggestions" aria-label="Sample questions">
        <button class="suggestion" type="button" data-question="Compare holiday string lights across the vendors.">Holiday string lights</button>
        <button class="suggestion" type="button" data-question="Compare restaurant nitrile gloves by price and quality.">Restaurant gloves</button>
        <button class="suggestion" type="button" data-question="Compare brake pads by price, quality, and material.">Brake pads</button>
      </div>
      <p class="data-note">This demo uses example vendor data, not live prices. Do not enter private, customer, payment, or other sensitive information.</p>
    </form>
    {error}
    {answer}
  </main>
  <script>
    const form = document.querySelector("form");
    const button = document.getElementById("ask-button");
    const buttonLabel = document.getElementById("button-label");
    const loadingMessage = document.getElementById("loading-message");
    const question = document.getElementById("question");

    document.querySelectorAll(".suggestion").forEach((suggestion) => {
      suggestion.addEventListener("click", () => {
        question.value = suggestion.dataset.question;
        question.focus();
      });
    });

    form.addEventListener("submit", (event) => {
      if (!form.checkValidity()) return;
      event.preventDefault();
      button.disabled = true;
      button.setAttribute("aria-busy", "true");
      buttonLabel.textContent = "Thinking...";
      loadingMessage.classList.add("is-visible");
      form.submit();
    });
  </script>
</body>
</html>"""


def render_page(question="", answer=None, error=None):
    error_html = f'<p class="error" role="alert">{escape(error)}</p>' if error else ""
    answer_html = ""
    if answer is not None:
        answer_html = (
            '<section class="answer" aria-live="polite">'
            '<h2>Agent response</h2>'
            f'<div class="answer-content">{_render_markdown(answer)}</div></section>'
        )
    return (
        PAGE.replace("{error}", error_html)
        .replace("{answer}", answer_html)
        .replace("{question}", escape(question))
    )


def _render_inline_markdown(text):
    """Render a small safe subset of inline Markdown after escaping raw HTML."""
    def replace_match(match):
        if match.group(1) is not None:
            return f"<code>{match.group(1)}</code>"
        if match.group(2) is not None:
            return f"<strong>{match.group(2)}</strong>"
        return f"<em>{match.group(3)}</em>"

    return re.sub(
        r"`([^`]+)`|\*\*(.+?)\*\*|(?<!\*)\*([^*]+)\*(?!\*)",
        replace_match,
        escape(text),
    )


def _table_cells(line):
    line = line.strip()
    if line.startswith("|"):
        line = line[1:]
    if line.endswith("|"):
        line = line[:-1]
    return [cell.strip() for cell in line.split("|")]


def _is_table_separator(line):
    cells = _table_cells(line)
    return len(cells) > 1 and all(re.fullmatch(r":?-+:?", cell) for cell in cells)


def _render_comparison_cards(headers, rows):
    cards = []
    for row_number, row in enumerate(rows, start=1):
        row += [""] * max(0, len(headers) - len(row))
        title = row[0] or f"Option {row_number}"
        details = "".join(
            f"<div><dt>{_render_inline_markdown(header)}</dt>"
            f"<dd>{_render_inline_markdown(value)}</dd></div>"
            for header, value in zip(headers[1:], row[1:])
            if value
        )
        cards.append(
            '<article class="comparison-card">'
            f"<h3><span>{_render_inline_markdown(headers[0])}: </span>"
            f"{_render_inline_markdown(title)}</h3><dl>{details}</dl></article>"
        )
    return f'<div class="comparison-list">{"".join(cards)}</div>'


def _parse_pipe_table(lines):
    rows = []
    separator_index = None
    for line in lines:
        if _is_table_separator(line):
            separator_index = len(rows)
        else:
            rows.append(_table_cells(line))

    if not rows or len(rows[0]) < 2:
        return None
    if separator_index is None and len(rows) < 2:
        return None
    if separator_index is not None and separator_index != 1:
        return None

    headers = rows[0]
    data_rows = rows[1:]
    if not data_rows or not all(len(row) > 1 for row in data_rows):
        return None
    return headers, data_rows


def _render_markdown(text):
    """Render headings, paragraphs, lists, and comparison cards without raw HTML."""
    lines = text.splitlines()
    output = []
    paragraph = []
    list_tag = None
    list_items = []

    def flush_paragraph():
        if paragraph:
            output.append(f"<p>{_render_inline_markdown(' '.join(paragraph))}</p>")
            paragraph.clear()

    def flush_list():
        nonlocal list_tag
        if list_items:
            items = "".join(f"<li>{_render_inline_markdown(item)}</li>" for item in list_items)
            output.append(f"<{list_tag}>{items}</{list_tag}>")
            list_items.clear()
        list_tag = None

    index = 0
    while index < len(lines):
        line = lines[index]
        stripped = line.strip()
        if not stripped:
            flush_paragraph()
            flush_list()
            index += 1
            continue

        if "|" in line:
            pipe_lines = []
            end_index = index
            while end_index < len(lines) and lines[end_index].strip() and "|" in lines[end_index]:
                pipe_lines.append(lines[end_index])
                end_index += 1
            table = _parse_pipe_table(pipe_lines)
            if table:
                flush_paragraph()
                flush_list()
                output.append(_render_comparison_cards(*table))
                index = end_index
                continue

        heading = re.match(r"^(#{1,3})\s+(.+)$", stripped)
        if heading:
            flush_paragraph()
            flush_list()
            level = len(heading.group(1))
            output.append(
                f"<h{level}>{_render_inline_markdown(heading.group(2))}</h{level}>"
            )
            index += 1
            continue

        if re.fullmatch(r"(?:-{3,}|\*{3,}|_{3,})", stripped):
            flush_paragraph()
            flush_list()
            output.append("<hr>")
            index += 1
            continue

        bullet = re.match(r"^\s*[-*+]\s+(.+)$", line)
        numbered = re.match(r"^\s*\d+[.)]\s+(.+)$", line)
        if bullet or numbered:
            flush_paragraph()
            current_tag = "ul" if bullet else "ol"
            if list_tag and list_tag != current_tag:
                flush_list()
            list_tag = current_tag
            list_items.append((bullet or numbered).group(1))
            index += 1
            continue

        flush_list()
        paragraph.append(stripped)
        index += 1

    flush_paragraph()
    flush_list()
    return "\n".join(output)


class CatalogIQHandler(BaseHTTPRequestHandler):
    """Serve a simple local form and delegate answers to the existing agent."""

    def do_GET(self):
        if self.path != "/":
            self.send_error(404)
            return
        self._send_html(render_page())

    def do_POST(self):
        if self.path != "/":
            self.send_error(404)
            return

        try:
            content_length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            content_length = 0
        if content_length > 16_384:
            self.send_error(413, "Question is too long")
            return

        form = parse_qs(self.rfile.read(content_length).decode("utf-8"))
        question = form.get("question", [""])[0].strip()
        if not question:
            self._send_html(render_page(error="Enter a question before submitting."), 400)
            return

        try:
            answer = asyncio.run(ask_agent(question))
        except Exception as error:
            print(f"[web] Agent request failed ({type(error).__name__})")
            self._send_html(
                render_page(
                    question,
                    error="CatalogIQ could not finish this request. Try again, or ask the person running CatalogIQ to check its setup.",
                ),
                500,
            )
            return

        self._send_html(render_page(question, answer=answer))

    def _send_html(self, content, status=200):
        encoded = content.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)

    def log_message(self, format, *args):
        print(f"[web] {format % args}")


if __name__ == "__main__":
    host = os.environ.get("CATALOGIQ_HOST", "127.0.0.1")
    port = int(os.environ.get("CATALOGIQ_PORT", "5001"))
    server = ThreadingHTTPServer((host, port), CatalogIQHandler)
    print(f"CatalogIQ is running on this computer: http://127.0.0.1:{port}")
    if host not in ("127.0.0.1", "localhost"):
        print("[web] Network access is enabled. Use only on a trusted private network.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
