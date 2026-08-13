/* Robotics for AI Engineers — interactive components (vanilla JS, no build step).
 *
 * <quiz-bank src="BANK_ID">      — interactive MCQ/numeric quiz, YAML-authored,
 *                                  converted to JSON at mkdocs build time.
 * <code-exercise src="EX_ID">    — DataCamp-style in-browser Python exercise
 *                                  (CodeMirror editor + Pyodide in a Web Worker).
 *
 * Progress persists in localStorage under "rai.*" keys. No backend.
 */
(function () {
  "use strict";

  // Site base URL, derived from this script's own <script src>.
  var SITE_BASE = (function () {
    var s = document.currentScript;
    if (s && s.src) return s.src.replace(/javascripts\/interactive\.js.*$/, "");
    return "/";
  })();

  function fetchJSON(rel) {
    return fetch(SITE_BASE + rel).then(function (r) {
      if (!r.ok) throw new Error("HTTP " + r.status + " for " + rel);
      return r.json();
    });
  }

  function store(key, val) {
    try { localStorage.setItem("rai." + key, JSON.stringify(val)); } catch (e) { /* private mode */ }
  }
  function load(key) {
    try {
      var v = localStorage.getItem("rai." + key);
      return v ? JSON.parse(v) : null;
    } catch (e) { return null; }
  }

  // Minimal markdown: escapes HTML, then renders `code`, **bold**, newlines.
  // MathJax \( \) spans pass through untouched and are typeset afterwards.
  function mdLite(text) {
    var h = String(text)
      .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
    // Emphasis must not reach inside code: the asterisks in `a * b` are
    // multiplication and `se2(*MOUNT)` is unpacking. So lift code spans out
    // first and put them back afterwards.
    //
    // The placeholder can safely use angle brackets: every literal "<" in the
    // input became "&lt;" on the line above, so "<0>" cannot collide with
    // anything the author wrote.
    var spans = [];
    h = h.replace(/`([^`]+)`/g, function (_, inner) {
      spans.push(inner);
      return "<" + (spans.length - 1) + ">";
    });
    h = h.replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>");
    h = h.replace(/\*([^*\n]+)\*/g, "<em>$1</em>");
    h = h.replace(/<(\d+)>/g, function (_, i) {
      return "<code>" + spans[i] + "</code>";
    });
    return h.replace(/\n/g, "<br>");
  }

  function typeset(el) {
    if (window.MathJax && window.MathJax.typesetPromise) {
      window.MathJax.typesetPromise([el]).catch(function () {});
    }
  }

  function el(tag, cls, html) {
    var e = document.createElement(tag);
    if (cls) e.className = cls;
    if (html !== undefined) e.innerHTML = html;
    return e;
  }

  /* ------------------------------------------------------------------ *
   *  Diagrams
   *
   *  Material's built-in mermaid support replaces the <pre> with an empty
   *  <div class="mermaid"> and never inserts the SVG, so every diagram on
   *  the site rendered as a blank gap. mermaid itself is fine — calling
   *  render() by hand returns a valid SVG — so we load a pinned mermaid and
   *  drive it here, off a fence class Material does not claim.
   * ------------------------------------------------------------------ */

  var diagramSeq = 0;

  function renderDiagrams() {
    var blocks = [].slice.call(document.querySelectorAll("pre.rai-diagram > code"));
    if (!blocks.length || !window.mermaid) return;
    var slate = document.body.getAttribute("data-md-color-scheme") === "slate";
    try {
      window.mermaid.initialize({
        startOnLoad: false,
        securityLevel: "strict",
        theme: slate ? "dark" : "default",
        flowchart: { curve: "basis" }
      });
    } catch (e) { return; }

    blocks.forEach(function (code) {
      var host = el("div", "mermaid");
      // Keep the source: the palette toggle does not reload the page, so a
      // theme flip has to re-render from something.
      host.dataset.src = code.textContent;
      code.parentNode.parentNode.replaceChild(host, code.parentNode);
      drawDiagram(host);
    });
  }

  function drawDiagram(host) {
    var id = "rai-mmd-" + (diagramSeq++);
    try {
      var out = window.mermaid.render(id, host.dataset.src);
      // mermaid 10 returns a promise; guard in case a future build does not.
      if (out && typeof out.then === "function") {
        out.then(function (r) { host.innerHTML = r.svg; })
           .catch(function (err) { host.textContent = "Diagram failed: " + err.message; });
      } else if (typeof out === "string") {
        host.innerHTML = out;
      }
    } catch (err) {
      host.textContent = "Diagram failed: " + err.message;
    }
  }

  /* Material's palette toggle swaps colours without reloading, which would
   * otherwise leave light diagrams on a dark page. */
  function watchDiagramTheme() {
    if (!window.MutationObserver) return;
    var last = document.body.getAttribute("data-md-color-scheme");
    new MutationObserver(function () {
      var now = document.body.getAttribute("data-md-color-scheme");
      if (now === last) return;
      last = now;
      var hosts = [].slice.call(document.querySelectorAll("div.mermaid[data-src]"));
      if (!hosts.length || !window.mermaid) return;
      try {
        window.mermaid.initialize({
          startOnLoad: false,
          securityLevel: "strict",
          theme: now === "slate" ? "dark" : "default",
          flowchart: { curve: "basis" }
        });
      } catch (e) { return; }
      hosts.forEach(drawDiagram);
    }).observe(document.body, { attributes: true, attributeFilter: ["data-md-color-scheme"] });
  }

  /* ------------------------------------------------------------------ *
   *  Quiz bank
   * ------------------------------------------------------------------ */

  var QuizBank = /** @class */ (function () {
    function attach(host) {
      var id = host.getAttribute("src");
      fetchJSON("assets/generated/quizzes/" + id + ".json")
        .then(function (bank) { render(host, id, bank); })
        .catch(function (e) {
          host.appendChild(el("div", "rai-card", "Quiz bank <code>" + id + "</code> failed to load: " + e.message));
        });
    }

    function render(host, bankId, bank) {
      var card = el("div", "rai-card");
      var header = el("div", "rai-bank-header");
      header.appendChild(el("span", "", bank.title || "Check your understanding"));
      var score = el("span", "rai-score", "");
      header.appendChild(score);
      card.appendChild(header);

      var state = load("quiz." + bankId) || {};

      function updateScore() {
        var correct = 0;
        bank.questions.forEach(function (q) {
          if (state[q.id] && state[q.id].correct) correct++;
        });
        score.textContent = correct + " / " + bank.questions.length + " correct";
        store("quiz." + bankId, state);
      }

      bank.questions.forEach(function (q, idx) {
        card.appendChild(renderQuestion(q, idx + 1, state, updateScore));
      });

      updateScore();
      host.appendChild(card);
      typeset(card);
    }

    function renderQuestion(q, num, state, onChange) {
      var wrap = el("div", "rai-q");
      var prompt = el("div", "rai-q-prompt");
      prompt.innerHTML =
        '<span class="rai-q-num">' + num + ".</span>" + mdLite(q.prompt) +
        (q.difficulty ? '<span class="rai-q-tag">' + q.difficulty + "</span>" : "");
      wrap.appendChild(prompt);

      var inputName = "rai-" + q.id + "-" + Math.random().toString(36).slice(2, 7);
      var body = el("div");
      wrap.appendChild(body);

      var feedback = el("div", "rai-feedback");
      var checkBtn = el("button", "rai-btn", "Check");
      var retryBtn = el("button", "rai-btn rai-btn-ghost", "Retry");
      retryBtn.style.display = "none";

      function buildOptions() {
        body.innerHTML = "";
        feedback.textContent = "";
        feedback.className = "rai-feedback";
        if (q.type === "numeric") {
          var input = el("input", "rai-numeric-input");
          input.type = "text";
          input.placeholder = q.placeholder || "numeric answer";
          body.appendChild(input);
        } else {
          var kind = q.type === "multi" ? "checkbox" : "radio";
          q.options.forEach(function (opt, i) {
            var label = el("label", "rai-opt");
            var inp = document.createElement("input");
            inp.type = kind;
            inp.name = inputName;
            inp.value = String(i);
            label.appendChild(inp);
            label.appendChild(el("span", "", mdLite(opt.text)));
            body.appendChild(label);
          });
        }
      }

      function check() {
        var correct = false;
        if (q.type === "numeric") {
          var input = body.querySelector("input");
          var v = parseFloat(input.value.replace(",", "."));
          var tol = q.tolerance !== undefined ? q.tolerance : 1e-3;
          correct = isFinite(v) && Math.abs(v - q.answer) <= tol;
          feedback.textContent = correct
            ? "Correct." : "Not quite" + (q.hint ? " — " + q.hint : ".");
          if (correct && q.explanation) feedback.textContent += " " + q.explanation;
        } else {
          var chosen = [].slice.call(body.querySelectorAll("input:checked"))
            .map(function (i) { return parseInt(i.value, 10); });
          if (!chosen.length) { feedback.textContent = "Pick an answer first."; return; }
          var right = q.options
            .map(function (o, i) { return o.correct ? i : -1; })
            .filter(function (i) { return i >= 0; });
          correct = chosen.length === right.length &&
            chosen.every(function (c) { return right.indexOf(c) >= 0; });

          [].slice.call(body.querySelectorAll(".rai-opt")).forEach(function (label, i) {
            var opt = q.options[i];
            var picked = chosen.indexOf(i) >= 0;
            label.querySelector("input").disabled = true;
            if (opt.correct) label.classList.add("rai-correct");
            else if (picked) label.classList.add("rai-wrong");
            if ((picked || opt.correct) && opt.explanation) {
              var ex = el("div", "rai-explain", mdLite(opt.explanation));
              label.insertAdjacentElement("afterend", ex);
            }
          });
          feedback.textContent = correct ? "Correct." : "Not quite — see the notes above.";
        }
        feedback.classList.add(correct ? "ok" : "bad");
        state[q.id] = { correct: correct, answered: true };
        onChange();
        checkBtn.style.display = "none";
        retryBtn.style.display = "";
        typeset(wrap);
      }

      checkBtn.addEventListener("click", check);
      retryBtn.addEventListener("click", function () {
        buildOptions();
        checkBtn.style.display = "";
        retryBtn.style.display = "none";
      });

      buildOptions();
      wrap.appendChild(checkBtn);
      wrap.appendChild(retryBtn);
      wrap.appendChild(feedback);
      return wrap;
    }

    return { attach: attach };
  })();

  /* ------------------------------------------------------------------ *
   *  Python runtime (Pyodide in a Web Worker), shared across exercises
   * ------------------------------------------------------------------ */

  var Py = {
    worker: null,
    seq: 0,
    pending: {},
    ensure: function () {
      if (!this.worker) {
        var self_ = this;
        this.worker = new Worker(SITE_BASE + "javascripts/py-worker.js");
        this.worker.onmessage = function (e) {
          var d = e.data;
          var p = self_.pending[d.id];
          if (!p) return;
          if (d.type === "progress") { if (p.onProgress) p.onProgress(d.msg); return; }
          delete self_.pending[d.id];
          p.resolve(d.result);
        };
        this.worker.onerror = function (err) {
          Object.keys(self_.pending).forEach(function (id) {
            self_.pending[id].resolve({
              status: "error", stdout: "",
              error: "Python runtime failed to load (network required for first run): " + err.message,
            });
            delete self_.pending[id];
          });
        };
      }
      return this.worker;
    },
    run: function (payload, onProgress) {
      var self_ = this;
      return new Promise(function (resolve) {
        var id = ++self_.seq;
        self_.pending[id] = { resolve: resolve, onProgress: onProgress };
        self_.ensure().postMessage({
          id: id, setup: payload.setup || "", code: payload.code || "", tests: payload.tests || "",
        });
      });
    },
  };

  /* ------------------------------------------------------------------ *
   *  Code exercise
   * ------------------------------------------------------------------ */

  var CodeExercise = /** @class */ (function () {
    function attach(host) {
      var id = host.getAttribute("src");
      fetchJSON("assets/generated/exercises/" + id + ".json")
        .then(function (spec) { render(host, id, spec); })
        .catch(function (e) {
          host.appendChild(el("div", "rai-card", "Exercise <code>" + id + "</code> failed to load: " + e.message));
        });
    }

    /* The learner never sees setup_code, so a name alone leaves them guessing
     * at signatures. Generated from the real objects at build time. */
    function providedPanel(items) {
      var d = document.createElement("details");
      d.className = "rai-provided";
      var s = document.createElement("summary");
      var nfn = items.filter(function (i) { return i.kind !== "constant"; }).length;
      s.textContent = "Provided in this exercise — " + items.length + " object" +
        (items.length === 1 ? "" : "s") + (nfn ? " (" + nfn + " callable)" : "");
      d.appendChild(s);
      var dl = el("div", "rai-provided__list");
      items.forEach(function (it) {
        var row = el("div", "rai-provided__item");
        var sig = el("code", "rai-provided__sig");
        sig.textContent = it.signature || (it.name + " = " + it.value);
        row.appendChild(sig);
        if (it.summary) row.appendChild(el("div", "rai-provided__doc", mdLite(it.summary)));
        // A signature names the parameters; it does not say what they mean
        // or what units they are in, and the source is hidden.
        if ((it.params || []).length || it.returns) {
          var tbl = document.createElement("table");
          tbl.className = "rai-provided__params";
          var addRow = function (label, type, doc, cls) {
            var tr = tbl.insertRow();
            if (cls) tr.className = cls;
            var c0 = tr.insertCell();
            var code = document.createElement("code");
            code.textContent = label;
            c0.appendChild(code);
            var c1 = tr.insertCell();
            if (type) {
              var em = document.createElement("em");
              em.textContent = type;
              c1.appendChild(em);
            }
            tr.insertCell().innerHTML = mdLite(doc);
          };
          (it.params || []).forEach(function (pm) {
            addRow(pm.name, pm.type, pm.doc, "");
          });
          if (it.returns) addRow("returns", it.returns.type, it.returns.doc, "is-return");
          row.appendChild(tbl);
        }
        if ((it.notes || []).length) {
          var ul = document.createElement("ul");
          ul.className = "rai-provided__notes";
          it.notes.forEach(function (n) {
            var li = document.createElement("li");
            li.innerHTML = mdLite(n);
            ul.appendChild(li);
          });
          row.appendChild(ul);
        }
        if (it.example) {
          var ex = el("pre", "rai-provided__eg");
          // Output is computed at build time by actually running the call, so
          // a worked example here can never drift from the code.
          ex.textContent = ">>> " + it.example +
            (it.example_out !== undefined ? "\n" + it.example_out : "");
          row.appendChild(ex);
        }
        dl.appendChild(row);
      });
      d.appendChild(dl);
      return d;
    }

    /* Editor display preferences, shared across every exercise on the site.
     * The editor's column is otherwise fixed by the page layout, so long
     * lines scroll out of view with no recourse; these give the reader font
     * size, line wrapping (default ON, which removes horizontal scrolling
     * entirely) and a wide mode that breaks the card out of the text column.
     * One setting, every editor, persisted. */
    var PREFS_KEY = "editor.prefs";
    var editorRegistry = [];

    function editorPrefs() {
      var p = load(PREFS_KEY) || {};
      return {
        fontPx: Math.min(24, Math.max(10, p.fontPx || 13)),
        wrap: p.wrap !== false,          // default: wrap long lines
        wide: !!p.wide,
      };
    }

    function applyPrefsTo(entry, prefs) {
      entry.wrapEl.style.fontSize = prefs.fontPx + "px";
      entry.card.classList.toggle("rai-wide", prefs.wide);
      if (entry.cm) {
        entry.cm.setOption("lineWrapping", prefs.wrap);
        entry.cm.refresh();
      } else {
        entry.ta.wrap = prefs.wrap ? "soft" : "off";
      }
    }

    function updatePrefs(mutate) {
      var prefs = editorPrefs();
      mutate(prefs);
      store(PREFS_KEY, prefs);
      editorRegistry.forEach(function (entry) {
        if (document.contains(entry.card)) applyPrefsTo(entry, prefs);
      });
    }

    function editorToolbar() {
      var bar = el("span", "rai-ed-tools");
      [["A−", "Smaller editor text", function (p) { p.fontPx = Math.max(10, p.fontPx - 1); }],
       ["A+", "Larger editor text", function (p) { p.fontPx = Math.min(24, p.fontPx + 1); }],
       ["↩", "Wrap long lines (no horizontal scrolling)", function (p) { p.wrap = !p.wrap; }],
       ["⇔", "Wide editor (use the full window width)", function (p) { p.wide = !p.wide; }],
      ].forEach(function (spec) {
        var b = el("button", "rai-ed-btn", spec[0]);
        b.type = "button";
        b.title = spec[2] ? spec[1] : spec[1];
        b.addEventListener("click", function () { updatePrefs(spec[2]); paintToolbars(); });
        bar.appendChild(b);
      });
      return bar;
    }

    function paintToolbars() {
      var prefs = editorPrefs();
      [].slice.call(document.querySelectorAll(".rai-ed-tools")).forEach(function (bar) {
        var btns = bar.querySelectorAll(".rai-ed-btn");
        if (btns[2]) btns[2].classList.toggle("is-on", prefs.wrap);
        if (btns[3]) btns[3].classList.toggle("is-on", prefs.wide);
      });
    }

    function render(host, exId, spec) {
      var card = el("div", "rai-card");
      var header = el("div", "rai-bank-header");
      header.appendChild(el("span", "rai-ex-title", "🧪 " + spec.title));
      var right = el("span", "rai-ex-right");
      right.appendChild(editorToolbar());
      var status = el("span", "rai-status", "not attempted");
      right.appendChild(status);
      header.appendChild(right);
      card.appendChild(header);
      if (spec.description) card.appendChild(el("div", "rai-ex-desc", mdLite(spec.description)));
      if ((spec.provided || []).length) card.appendChild(providedPanel(spec.provided));

      var saved = load("ex." + exId) || {};
      if (saved.passed) setStatus("pass");

      var wrap = el("div", "rai-editor-wrap");
      var ta = document.createElement("textarea");
      ta.className = "rai-plain";
      ta.value = saved.code || spec.starter_code || "";
      ta.spellcheck = false;
      wrap.appendChild(ta);
      card.appendChild(wrap);

      var cm = null;
      var prefs = editorPrefs();
      if (window.CodeMirror) {
        cm = window.CodeMirror.fromTextArea(ta, {
          mode: "python", lineNumbers: true, indentUnit: 4, viewportMargin: Infinity,
          lineWrapping: prefs.wrap,
        });
        cm.on("change", persistSoon);
      } else {
        ta.addEventListener("input", persistSoon);
      }
      var regEntry = { card: card, wrapEl: wrap, cm: cm, ta: ta };
      editorRegistry.push(regEntry);
      applyPrefsTo(regEntry, prefs);
      paintToolbars();
      function getCode() { return cm ? cm.getValue() : ta.value; }
      function setCode(v) { if (cm) cm.setValue(v); else ta.value = v; }

      var persistTimer = null;
      function persistSoon() {
        clearTimeout(persistTimer);
        persistTimer = setTimeout(function () {
          saved.code = getCode();
          store("ex." + exId, saved);
        }, 500);
      }

      function setStatus(kind) {
        status.className = "rai-status" + (kind ? " " + kind : "");
        status.textContent = kind === "pass" ? "passed ✓" : kind === "fail" ? "not passing" : "not attempted";
      }

      var output = el("div", "rai-output");
      var hintBox = el("div");
      var solBox = el("div", "rai-solution");
      var hintIdx = 0;

      var runBtn = el("button", "rai-btn", "▶ Run");
      var submitBtn = el("button", "rai-btn", "✓ Submit");
      var hintBtn = el("button", "rai-btn rai-btn-ghost", "Hint");
      var resetBtn = el("button", "rai-btn rai-btn-ghost", "Reset");
      var solBtn = el("button", "rai-btn rai-btn-ghost", "Show solution");

      function execute(withTests) {
        output.textContent = "";
        runBtn.disabled = submitBtn.disabled = true;
        var progressLine = el("div", "", "Starting…");
        output.appendChild(progressLine);
        Py.run(
          { setup: spec.setup_code, code: getCode(), tests: withTests ? spec.tests : "" },
          function (msg) { progressLine.textContent = msg; }
        ).then(function (res) {
          runBtn.disabled = submitBtn.disabled = false;
          output.textContent = "";
          if (res.stdout) output.appendChild(el("div", "", "").appendChild(document.createTextNode(res.stdout)).parentNode);
          if (res.status === "pass") {
            output.appendChild(el("div", "okline", "✓ All checks passed. Nicely done."));
            saved.passed = true;
            store("ex." + exId, saved);
            setStatus("pass");
          } else if (res.status === "fail") {
            output.appendChild(el("div", "err", "✗ Check failed: " + res.error));
            setStatus("fail");
          } else if (res.status === "error") {
            output.appendChild(el("div", "err", res.error));
            if (withTests) setStatus("fail");
          } else if (!res.stdout) {
            output.appendChild(el("div", "", "(no output — use print() to inspect values)"));
          }
        });
      }

      runBtn.addEventListener("click", function () { execute(false); });
      submitBtn.addEventListener("click", function () { execute(true); });
      hintBtn.addEventListener("click", function () {
        var hints = spec.hints || [];
        if (!hints.length) return;
        if (hintIdx < hints.length) {
          hintBox.appendChild(el("div", "rai-hint", "Hint " + (hintIdx + 1) + "/" + hints.length + ": " + mdLite(hints[hintIdx])));
          hintIdx++;
          typeset(hintBox);
        }
        if (hintIdx >= hints.length) hintBtn.disabled = true;
      });
      resetBtn.addEventListener("click", function () {
        if (confirm("Reset this exercise to the starter code?")) {
          setCode(spec.starter_code || "");
          persistSoon();
        }
      });
      solBtn.addEventListener("click", function () {
        if (solBox.childNodes.length) { solBox.innerHTML = ""; solBtn.textContent = "Show solution"; return; }
        if (!saved.passed && !confirm("Give it a real try first — show the solution anyway?")) return;
        var pre = el("pre");
        pre.textContent = spec.solution || "(no solution provided)";
        solBox.appendChild(pre);
        solBtn.textContent = "Hide solution";
      });

      card.appendChild(runBtn);
      card.appendChild(submitBtn);
      if ((spec.hints || []).length) card.appendChild(hintBtn);
      card.appendChild(resetBtn);
      if (spec.solution) card.appendChild(solBtn);
      card.appendChild(output);
      card.appendChild(hintBox);
      card.appendChild(solBox);
      host.appendChild(card);
      typeset(card);
      if (cm) setTimeout(function () { cm.refresh(); }, 50);
    }

    return { attach: attach };
  })();

  /* ------------------------------------------------------------------ */

  function init() {
    renderDiagrams();
    watchDiagramTheme();
    [].slice.call(document.querySelectorAll("quiz-bank")).forEach(QuizBank.attach);
    [].slice.call(document.querySelectorAll("code-exercise")).forEach(CodeExercise.attach);
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", init);
  else init();
})();
