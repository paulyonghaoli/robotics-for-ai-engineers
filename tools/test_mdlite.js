/*
 * Gate: the widget's markdown renderer must protect code spans.
 *
 * `mdLite` in docs/javascripts/interactive.js renders exercise descriptions,
 * hints, and quiz explanations. Emphasis must not reach inside a code span --
 * `a * b` is multiplication and `se2(*MOUNT)` is unpacking, not italics, and
 * an exponent like `f**K` is not bold. Substituting <code> first and then
 * running the bold/italic passes over the whole string does not protect
 * against this: a stray `*` or `**` inside a span can pair with a REAL
 * emphasis marker later in the text and bold or italicise everything
 * between them, breaking across the <code> boundary. This ported from the
 * llm-systems-for-data-scientists curriculum, where exactly that bug shipped
 * (`(1 - f**K) / (1 - f)` paired its `**` with a later `**bold**`).
 *
 * No other gate can see this. The source YAML is correct markdown, the word
 * counts are unchanged, the components resolve, and the page renders without
 * an error; only the visible output is wrong. So the check is on the
 * renderer itself, exercised the way the browser exercises it.
 *
 *     node tools/test_mdlite.js
 */

"use strict";

const fs = require("fs");
const path = require("path");

const SRC = path.join(__dirname, "..", "docs", "javascripts", "interactive.js");
const source = fs.readFileSync(SRC, "utf8");

// Parse the whole file first: a syntax error here breaks every widget on the
// site, and mkdocs will happily publish it.
try {
  new Function(source);
} catch (e) {
  console.error("interactive.js does not parse: " + e.message);
  process.exit(1);
}

const start = source.indexOf("function mdLite(text)");
const end = source.indexOf("function typeset(el)");
if (start === -1 || end === -1 || end < start) {
  console.error("could not locate mdLite in interactive.js — has it been renamed or moved?");
  process.exit(1);
}
const mdLite = new Function(source.slice(start, end) + "; return mdLite;")();

const cases = [
  {
    name: "multiplication in a code span does not pair with later bold",
    input: "the term `a * b` decays and the **damping term** is `k_d * d`",
    expect: "the term <code>a * b</code> decays and the " +
            "<strong>damping term</strong> is <code>k_d * d</code>",
  },
  {
    name: "unpacking * in a code span stays literal",
    input: "`se2(*MOUNT)` is T_base_lidar and **MOUNT** is the pose",
    expect: "<code>se2(*MOUNT)</code> is T_base_lidar and " +
            "<strong>MOUNT</strong> is the pose",
  },
  {
    name: "exponent in a code span does not pair with later bold",
    input: "cost is `(1 - f**K) / (1 - f)` and the **success rate** is `1 - f**K`",
    expect: "cost is <code>(1 - f**K) / (1 - f)</code> and the " +
            "<strong>success rate</strong> is <code>1 - f**K</code>",
  },
  {
    name: "two code spans each containing **",
    input: "`a**b` then `c**d`",
    expect: "<code>a**b</code> then <code>c**d</code>",
  },
  {
    name: "ordinary bold still renders",
    input: "this is **bold** text",
    expect: "this is <strong>bold</strong> text",
  },
  {
    name: "ordinary italic still renders",
    input: "this is *italic* text",
    expect: "this is <em>italic</em> text",
  },
  {
    name: "a single * inside a code span does not pair with later italic",
    input: "the gust hits at `k == 40 * DT` in *this* world",
    expect: "the gust hits at <code>k == 40 * DT</code> in <em>this</em> world",
  },
  {
    name: "bold may still contain a code span",
    input: "**see `x` now**",
    expect: "<strong>see <code>x</code> now</strong>",
  },
  {
    name: "italic may still contain a code span",
    input: "*see `x` now*",
    expect: "<em>see <code>x</code> now</em>",
  },
  {
    name: "a lone ** inside a code span stays literal",
    input: "the value `0.2**3` is small",
    expect: "the value <code>0.2**3</code> is small",
  },
  {
    name: "html is escaped before anything else",
    input: "a <script>alert(1)</script> b",
    expect: "a &lt;script&gt;alert(1)&lt;/script&gt; b",
  },
  {
    name: "newlines become breaks",
    input: "one\ntwo",
    expect: "one<br>two",
  },
];

let failed = 0;
for (const c of cases) {
  const got = mdLite(c.input);
  if (got === c.expect) {
    console.log("  ok    " + c.name);
  } else {
    failed += 1;
    console.log("  FAIL  " + c.name);
    console.log("        input    " + JSON.stringify(c.input));
    console.log("        expected " + JSON.stringify(c.expect));
    console.log("        got      " + JSON.stringify(got));
  }
}

if (failed) {
  console.error("\n" + failed + " mdLite case(s) failed");
  process.exit(1);
}
console.log("\nall " + cases.length + " mdLite cases passed");
