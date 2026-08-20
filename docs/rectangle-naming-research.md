# Can "Cupertino Rectangle" keep the "Rectangle" name?

Research notes, 2026-08-20. Question: the kupertino repo's KWin script
`kwin-scripts/cupertino-rectangle/` ("Cupertino Rectangle") reimplements — behavior
only, no code copied — the 22 default keyboard actions of Rectangle.app
(github.com/rxhanson/rectangle, by Ryan Hanson, who also sells a commercial
"Rectangle Pro"). Is the name safe?

**This is research, not legal advice.**

Legend: **[verified]** = the primary source was fetched directly.
**[inference]** = conclusion drawn from verified facts. **[unverified]** = could
not be confirmed against a primary source.

---

## TL;DR verdict

**Keep the name "Cupertino Rectangle" — with a clear non-affiliation note.
Confidence: high** for descriptive references in docs, **moderate-to-high** for
the name itself.

Why:

1. Rectangle is MIT-licensed with **no trademark clause, no brand policy, and no
   trademark notice anywhere** on the repo or rectangleapp.com [verified]. Note:
   copyright licenses don't grant trademark rights either way — the point is that
   the author has published no naming restrictions and asserted no mark.
2. No US trademark registration for "Rectangle"/"Rectangle Pro" (window
   management) was found via web/Justia search; direct USPTO database query
   could not be completed [unverified — see §1]. Any rights would be common-law
   only, and "rectangle" is a dictionary word for a rectangular-window-snapping
   app — a weak, arguably descriptive mark [inference].
3. **Prior art is abundant**: at least four existing Linux projects already use
   "Rectangle" in their names (`kwin-rectangle`, 70 stars, since 2021;
   `rectangle-kwinscript`; `kwin-mac-rectangle`; `Rectangle-gnome-extension`),
   with no evidence of objection from the Rectangle author [verified].
4. Naming competitors descriptively is standard practice in this niche (Loop's
   README compares itself by name against Rectangle, Rectangle Pro, Magnet,
   Moom, etc.) [verified].
5. Residual risk is confusion/implied-endorsement, not the word itself. It is
   near-eliminated by a README/metadata line such as: *"Not affiliated with or
   endorsed by Rectangle.app or Ryan Hanson. Rectangle is a macOS app by Ryan
   Hanson; this is an independent KWin reimplementation of its default
   shortcuts."* [inference from the nominative-fair-use factors, §3].

The lowest-risk courtesy step (optional): a short note or issue to rxhanson
saying "we named our KDE port Cupertino Rectangle in homage — shout if you'd
rather we didn't." Rectangle itself is openly "based on Spectacle" and kept
Spectacle's behavior under a new name, so the author operates in exactly this
tradition [verified].

---

## 1. Rectangle's license and trademark posture

### License [verified]

Source: <https://raw.githubusercontent.com/rxhanson/Rectangle/master/LICENSE>

- **MIT License.**
- Copyright line: `Copyright (c) 2019-2026 Ryan Hanson`
- Carries a second attribution: *"Based on the Spectacle app, Copyright (c) 2017
  Eric Czarny eczarny@gmail.com"* — Rectangle is itself a derivative of an
  earlier open-source window manager.
- Standard MIT text; **no trademark clause** (MIT never includes one; unlike
  e.g. Apache-2.0 §6, it is simply silent on trademarks).

Since no code was copied, the MIT license imposes no obligations on kupertino at
all; it is relevant only as evidence of the author's permissive posture and the
absence of any naming restriction [inference].

### README [verified]

Source: <https://raw.githubusercontent.com/rxhanson/Rectangle/master/README.md>

- No trademark statement, brand-usage guidance, or naming restrictions of any
  kind.
- Describes itself as *"a window management app based on Spectacle, written in
  Swift."*
- Confirms the commercial product: *"The Rectangle Pro app is entirely built on
  top of Rectangle."*

### rectangleapp.com [verified]

Source: <https://rectangleapp.com>

- **No ™ or ® symbols anywhere on the page.**
- Footer: `© Ryan Hanson 2018-2026` plus links to Privacy Policy/ToS, EULA, and
  a Rectangle Pro refund policy — but **no trademark policy or brand
  guidelines**.
- Markets the free app as "Free and Open Source" and calls itself *"nearly a
  complete drop-in replacement for Spectacle"* — i.e., the author built his own
  brand by openly positioning against a named predecessor app.

### US trademark registration [unverified — searched, nothing found]

- Web searches ("Rectangle Pro trademark USPTO Ryan Hanson", Justia Trademarks
  queries) surfaced **no registration** of "Rectangle" or "Rectangle Pro" for
  window-management software or by Ryan Hanson. Hits were unrelated (e.g. "DJ
  RECTANGLE", reg. 2590224; Xiamen Rectangle Trading Co.).
  Sources: <https://trademarks.justia.com/757/08/dj-rectangle-75708069.html>,
  search results via <https://www.uspto.gov/trademarks/search>.
- Direct USPTO queries could not be completed from this environment: the new
  tmsearch.uspto.gov is a JavaScript app with no anonymous API, and
  trademarks.justia.com returned HTTP 403 to direct fetches. **So "no
  registration exists" is probable but not proven.** A definitive answer needs a
  manual search at <https://tmsearch.uspto.gov>.
- Even without registration, US common-law trademark rights can exist through
  use in commerce (Rectangle Pro is sold). But "Rectangle" for an app that
  snaps windows into rectangles is highly descriptive of the product category,
  which makes it a weak mark that is hard to enforce broadly [inference].

---

## 2. Precedent: how comparable projects use competitors' names

### Loop (macOS window manager, github.com/MrKai77/Loop) [verified]

Source: <https://raw.githubusercontent.com/MrKai77/Loop/develop/README.md>

Loop's README contains a feature-comparison table whose column headers name
competitors directly: *"Loop, macOS 15+, Rectangle Pro, Rectangle, Magnet, Moom,
Swish, BetterTouchTool, Multitouch, Hammerspoon, Yabai, Amethyst, AeroSpace,
1Piece, Wins, MacsyZones."* Naming Rectangle (and the commercial Rectangle Pro)
in comparative material is done openly by a direct competitor.

### Amethyst (github.com/ianyh/Amethyst) [verified]

Source: <https://raw.githubusercontent.com/ianyh/Amethyst/development/README.md>

Describes itself as a *"Tiling window manager for macOS along the lines of
[xmonad](https://xmonad.org/)"* and maps its default shortcuts to xmonad's —
i.e., "app X, along the lines of app Y, with Y's keybindings" is an established
README idiom.

### Raycast [verified]

Source: <https://www.raycast.com/core-features/window-management>

Raycast's window-management marketing does **not** name Rectangle or any
competitor; it says only *"There are several highly regarded window manager apps
for Mac…"*. So commercial marketing copy tends to avoid naming competitors,
while open-source READMEs name them freely [inference from the contrast].

### Linux prior art: "Rectangle" already reused in project names [verified]

GitHub repository search (api.github.com, 2026-08-20):

| Repo | Created | Stars | Note |
|---|---|---|---|
| `acristoffers/kwin-rectangle` | 2021-06 | 70 | GPL-3.0 KWin shortcuts project, "Rectangle" in the name since 2021 |
| `Mohamed-Rajab-2112/Rectangle-gnome-extension` | 2025-04 | 0 | GNOME extension |
| `SyedAbuTalib/kwin-mac-rectangle` | 2026-05 | 0 | "macOS Rectangle-style window snapping shortcuts for KWin / Plasma 6" |
| `kobago/rectangle-kwinscript` | 2026-07 | 0 | "Rectangle written in KWin Script" |

Plus `ChrisDoohan/cycle-snap` describing itself as *"like the Rectangle window
manager on Mac OS"*. The most visible one (`kwin-rectangle`) has carried the
name publicly for 5 years. No takedowns, renames, or disputes were found in a
web search [inference: absence of evidence, but consistent with a
non-enforcement posture].

### The norm

Descriptive references ("Rectangle-style", "like Rectangle.app", comparison
tables naming Rectangle) are **standard, widespread practice** in this exact
niche, including by direct commercial competitors of Rectangle. Reuse of the
word "Rectangle" inside Linux project names is established prior art going back
to at least 2021.

---

## 3. Nominative fair use (US doctrine)

*New Kids on the Block v. News America Publishing, Inc.*, 971 F.2d 302 (9th
Cir. 1992) established the three-factor nominative fair use test. Sources:
<https://www.bgrow.com/post/new-kids-on-the-block-v-news-america-publishing-inc-971-f-2d-302-9th-cir-1992>,
<https://law.resource.org/pub/us/case/reporter/F3/279/279.F3d.796.00-55538.00-55537.00-55229.00-55009.html>
[verified against these case write-ups; not the original reporter]. The factors:

1. The product must not be readily identifiable without using the mark;
2. Only so much of the mark may be used as is reasonably necessary;
3. The use must not suggest sponsorship or endorsement by the mark holder.

(Note the circuit split: the 2nd Circuit folds these into its likelihood-of-
confusion analysis rather than treating them as a standalone defense —
<https://www.arnoldporter.com/en/perspectives/publications/2016/11/2016_11_16_second_circuit_expands_split__13324>.)

### (a) Descriptive references in docs/README — low risk

"Implements Rectangle.app's 22 default shortcuts" is the paradigm nominative
use: there is no way to say "compatible with Rectangle's muscle memory" without
saying "Rectangle" (factor 1); plain-text mention of the name, no logo, no
styling (factor 2); and phrasing like "reimplementation of", "not affiliated
with" negates endorsement (factor 3). This is the same use Loop and cycle-snap
make [inference; near-certainly safe].

### (b) "Rectangle" IN the project's own name — different risk profile

Nominative fair use protects using someone's mark **to refer to their product**.
"Cupertino Rectangle" uses the word **as part of this project's own brand**, so
the defense fits less cleanly — the classic analysis would instead be ordinary
likelihood-of-confusion. Why the profiles differ [inference]:

- In (a) the mark points at *their* product; in (b) it names *yours*. Courts are
  more skeptical of (b) because a product name is exactly where source
  confusion happens.
- Mitigating factors specific to this case: "rectangle" is a generic dictionary
  word and descriptive of the function (weak mark); no registration found; the
  products are on disjoint platforms (macOS vs. KDE Plasma) and the KWin script
  is free, so no lost sale; "Cupertino" prefix + the kupertino project context
  signal "homage/port", not origin; and multiple projects have used the name on
  Linux for years without incident.
- Aggravating factor: Rectangle Pro is a commercial product, so the author has
  a real financial interest in the name, and common-law rights don't require
  registration. If he ever objected, the cheap resolution is a rename — the
  realistic worst case is a polite request, not litigation [inference].

**Practical mitigation:** keep the compound name (never plain "Rectangle"),
never imitate the Rectangle logo/branding, and put a non-affiliation +
attribution line in the README and in
`kwin-scripts/cupertino-rectangle/metadata.json`'s description.

---

## 4. The Apple angle: "Cupertino"

- "Cupertino" is a California city name, not an Apple product name. Apple's own
  "Guidelines for Using Apple Trademarks" page **does not list "Cupertino"**
  among Apple's trademarks. Source (fetched 2026-08-20):
  <https://www.apple.com/legal/intellectual-property/guidelinesfor3rdparties.html>
  [verified]. Geographic terms are also generally not protectable as marks for
  unrelated parties' goods [inference].
- **Flutter precedent [verified]:** Google's Flutter ships an official
  "Cupertino" widget library — *"Beautiful and high-fidelity widgets that align
  with Apple's Human Interface Guidelines for iOS and macOS"* —
  <https://docs.flutter.dev/ui/widgets/cupertino>. A major corporation uses
  "Cupertino" as a public byword for "Apple-style" with no Apple objection.
  Strong precedent that "Cupertino" (and "kupertino") is safe.
- **"Mac"-prefixed names:** Apple's third-party guidelines *do* regulate "Mac"
  in product names — permitted only if the product is Mac-compatible, "Mac" is
  combined with a non-generic word, doesn't dominate the name, etc. (same URL
  as above). Caveat [unverified detail]: the page's Acceptable/Not-acceptable
  example lists came back garbled through automated fetching ("MacVenus"
  appeared on both sides in different fetches), so read the live page before
  relying on specific examples. **Not applicable here** — kupertino uses
  neither "Mac" nor "Apple" in any project name, which is the safer pattern
  anyway [inference].

---

## Bottom line

Nothing found in any primary source restricts use of the word "Rectangle": MIT
license with no trademark clause, no trademark notice or brand policy on the
repo or website, no registration found (registration status not fully
verifiable from here), and 5 years of unchallenged Linux prior art including
`kwin-rectangle`. Descriptive references are textbook nominative fair use.
Using the word inside the name "Cupertino Rectangle" is a step riskier in
theory, but weak-mark status, disjoint platforms, the distinguishing
"Cupertino" prefix, and community norms make it low risk in practice — add a
non-affiliation note, and optionally give rxhanson a friendly heads-up.
