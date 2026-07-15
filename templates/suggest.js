/* WTBS "Suggest an edit" widget.
   A dismissible corner panel, opened either from the persistent corner button
   or by selecting transcript text (which pre-fills the quote). Submissions POST
   to the Cloudflare Worker (window.WTBS.endpoint); with no endpoint it runs in
   local preview mode (shows the payload). */
(function () {
  var cfg = window.WTBS || {};
  var sel = { text: "", idx: null, context: "" };

  // --- floating button shown when transcript text is selected ---
  var btn = document.createElement("button");
  btn.className = "suggest-btn"; btn.textContent = "✎ Suggest edit"; btn.hidden = true;
  document.body.appendChild(btn);
  function hideBtn() { btn.hidden = true; }

  document.addEventListener("selectionchange", function () {
    var s = window.getSelection();
    var text = s && s.toString().trim();
    // the currently-visible transcript (article or raw)
    var transcript = document.querySelector(".transcript:not(.hidden)")
      || document.querySelector(".transcript");
    if (!text || text.length < 2 || !s.rangeCount) { return hideBtn(); }
    var range = s.getRangeAt(0);
    var anc = range.commonAncestorContainer;
    var ancEl = anc.nodeType === 1 ? anc : anc.parentElement;
    if (!transcript || !transcript.contains(ancEl)) { return hideBtn(); }
    // anchor to the turn where the selection starts (supports multi-line spans)
    var startEl = range.startContainer.nodeType === 1
      ? range.startContainer : range.startContainer.parentElement;
    var turn = startEl.closest(".turn");
    sel.text = text.replace(/\s+/g, " ");
    sel.idx = turn ? turn.getAttribute("data-idx") : null;
    sel.context = turn ? turn.textContent.trim().slice(0, 240) : sel.text.slice(0, 240);
    var rect = range.getBoundingClientRect();
    btn.style.top = (window.scrollY + rect.top - 42) + "px";
    btn.style.left = (window.scrollX + Math.max(rect.left, 8)) + "px";
    btn.hidden = false;
  });

  // --- persistent corner button ---
  var fab = document.createElement("button");
  fab.className = "suggest-fab"; fab.textContent = "✎ Suggest an edit";
  document.body.appendChild(fab);

  // --- corner panel ---
  var panel = document.createElement("div");
  panel.className = "suggest-modal";
  panel.innerHTML =
    '<form class="suggest-card" novalidate>' +
      '<div class="suggest-head"><h3>Suggest an edit</h3>' +
        '<button type="button" class="suggest-close" aria-label="Close">✕</button></div>' +
      '<p class="suggest-quote"></p>' +
      '<label>Type of change' +
        '<select name="type">' +
          '<option value="spelling">Spelling</option>' +
          '<option value="grammar">Grammar</option>' +
          '<option value="capitalization">Capitalization</option>' +
          '<option value="punctuation">Punctuation</option>' +
          '<option value="hyperlink">Hyperlink</option>' +
          '<option value="other">Other</option>' +
        '</select></label>' +
      '<label class="suggest-suggested">Your edit <span class="muted">(change the text below)</span>' +
        '<textarea name="suggested" rows="3" placeholder="How should it read?"></textarea></label>' +
      '<label class="suggest-url" hidden>URL to link to' +
        '<input name="url" type="url" placeholder="https://…"></label>' +
      '<div class="suggest-row">' +
        '<label>Your name<input name="name" type="text" required></label>' +
        '<label>Email<input name="email" type="email" required></label>' +
      '</div>' +
      '<label>Note <span class="muted">(optional)</span>' +
        '<textarea name="note" rows="2" placeholder="Anything else?"></textarea></label>' +
      '<input type="text" name="website" class="suggest-hp" tabindex="-1" autocomplete="off">' +
      '<div class="suggest-actions">' +
        '<button type="button" class="suggest-cancel">Cancel</button>' +
        '<button type="submit" class="suggest-submit">Send</button>' +
      '</div>' +
      '<p class="suggest-status" role="status"></p>' +
    '</form>';
  document.body.appendChild(panel);

  var form = panel.querySelector("form");
  var status = panel.querySelector(".suggest-status");
  var quote = panel.querySelector(".suggest-quote");
  var typeSel = form.type, urlField = panel.querySelector(".suggest-url");

  function open(withSelection) {
    if (!withSelection) { sel = { text: "", idx: null, context: "" }; }
    hideBtn();
    quote.textContent = sel.text ? "Original: “" + sel.text + "”"
      : "General suggestion — describe the change and where it is.";
    status.textContent = ""; status.className = "suggest-status";
    // Pre-fill the edit box with the highlighted words so the reader edits in place.
    form.suggested.value = sel.text || "";
    form.url.value = ""; form.note.value = "";
    urlField.hidden = typeSel.value !== "hyperlink";
    panel.classList.add("open"); fab.hidden = true;
    if (sel.text) { form.suggested.focus(); form.suggested.select(); } else { form.name.focus(); }
  }
  function close() { panel.classList.remove("open"); fab.hidden = false; }

  btn.addEventListener("click", function () { open(true); });
  fab.addEventListener("click", function () { open(false); });
  panel.querySelector(".suggest-close").addEventListener("click", close);
  panel.querySelector(".suggest-cancel").addEventListener("click", close);
  typeSel.addEventListener("change", function () { urlField.hidden = typeSel.value !== "hyperlink"; });
  document.addEventListener("keydown", function (e) { if (e.key === "Escape") close(); });
  document.addEventListener("mousedown", function (e) {
    if (panel.classList.contains("open") && !panel.contains(e.target)
        && e.target !== fab && e.target !== btn) { close(); }
  });

  form.addEventListener("submit", function (e) {
    e.preventDefault();
    if (form.website.value) return;                       // honeypot
    var name = form.name.value.trim(), email = form.email.value.trim();
    if (!name || !/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(email)) {
      status.textContent = "Please enter your name and a valid email.";
      status.className = "suggest-status err"; return;
    }
    if (typeSel.value === "hyperlink" && !form.url.value.trim()) {
      status.textContent = "Please provide the URL to link to.";
      status.className = "suggest-status err"; return;
    }
    if (sel.text && typeSel.value !== "hyperlink"
        && form.suggested.value.trim() === sel.text.trim() && !form.note.value.trim()) {
      status.textContent = "Edit the highlighted text (or add a note) before sending.";
      status.className = "suggest-status err"; return;
    }
    if (!sel.text && !form.suggested.value.trim() && !form.note.value.trim()) {
      status.textContent = "Please describe the change (or select the text it applies to).";
      status.className = "suggest-status err"; return;
    }
    var payload = {
      episode: cfg.episode, title: cfg.title, type: typeSel.value,
      original: sel.text, suggested: form.suggested.value.trim(), url: form.url.value.trim(),
      note: form.note.value.trim(), anchor_idx: sel.idx, context: sel.context,
      name: name, email: email, page: location.pathname, website: form.website.value
    };
    if (!cfg.endpoint) {
      status.className = "suggest-status ok";
      status.textContent = "Preview (no endpoint set). Payload: " + JSON.stringify(payload);
      return;
    }
    status.textContent = "Sending…"; status.className = "suggest-status";
    fetch(cfg.endpoint, { method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload) }).then(function (r) {
      if (!r.ok) throw new Error(r.status);
      status.className = "suggest-status ok";
      status.textContent = "Thank you! Your suggestion was submitted for review.";
      setTimeout(close, 1800);
    }).catch(function () {
      status.className = "suggest-status err";
      status.textContent = "Sorry — something went wrong. Please try again later.";
    });
  });
})();
