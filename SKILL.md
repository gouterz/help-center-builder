---
name: help-center-builder
description: Build or extend a product's help center (help docs, knowledge base, support articles, FAQ and how-to pages) straight from the product's own codebase. Covers inventorying every setting in the code, writing one self-explanatory page per customer question, capturing annotated screenshots of the live app with Claude in Chrome on a demo account, checking every claim against the live UI, running a privacy audit on text and images, and handing the work off on a branch to review and publish (GitBook, Mintlify, Docusaurus, Nextra, ReadMe, Intercom, Zendesk, Help Scout or plain markdown). Use this whenever someone wants help docs, a help center, a knowledge base, "document every setting", screenshots for their docs, or says their docs miss the small "how do I turn off X" questions, even if they never say "help center".
---

# Help center builder

Your job is to turn a product's code and live UI into accurate, public help pages. Each page answers one real customer question and shows annotated screenshots. Nothing internal about the product may leak into them.

The founder should end up with four things:

1. **New pages and images on a branch.** Leave them staged, or committed if the founder asks. Never push them.
2. **A review preview** they can read from start to finish.
3. **A handoff note** that covers where the work is and how to publish it. It also lists the privacy check results, the screenshots only they can take, bugs you found, existing pages that are now wrong, and every change you made in the demo account.
4. **Nothing published.** Only the founder decides when pages go live.

## Step 0: learn the founder's stack (first run)

Every founder's setup is different, so start by looking for a saved setup file at `.claude/help-center-setup.md` in the product repo.

- **If it exists,** read it, confirm in one line that it's still right ("Using the setup from last time: Mintlify docs in `/docs`, demo workspace Acme Demo. Anything changed?"), and continue.
- **If it doesn't,** this is the first run, so ask about the stack before doing anything else. Scan the workspace first so you can suggest answers instead of asking open questions. For example, if `docs.json` exists, offer "Mintlify, in `/docs`" as the likely answer.

Ask these questions together, in one message. Use a multiple-choice question tool if you have one.

1. **Docs platform and location.** Which platform hosts the help center (GitBook, Mintlify, Docusaurus, Nextra, ReadMe, Intercom, Zendesk, Help Scout, Notion, other)? Where do the docs files live (a repo path, or none for a hosted help center)?
2. **Publishing.** What makes a change go live (a merge to a branch, a deploy, a publish button)? Who does it? The default answer is: you prepare a branch and the founder publishes.
3. **Product code.** Where is the code for the app's screens, the backend and the parts customers see? Offer the folders you found.
4. **Browser account for screenshots.** Is Claude in Chrome set up and signed in? Which account is it signed in to, and what's its role (owner, admin or member)? Which demo workspace or project may you change? What must never be touched?
5. **Scope and audience.** Is this the whole product or specific areas? Is it for end users, admins or developers?
6. **Voice and extras.** Is there a style guide or tone to match? Can the founder share support questions or search terms, so the pages answer what customers really ask?

Save the answers to `.claude/help-center-setup.md` (write "unknown" rather than guessing), so the next run skips the questions. This file names internal paths and accounts, so keep it out of the published docs folder.

## Establish the rest of the setup

With the founder's answers in hand, fill in the details from the repo. Ask only about what you still can't find.

- **Docs source.** Find the repo path, the platform, the table-of-contents file, the image folder and what makes a change go live. `references/platforms.md` lists the files that identify each platform. If there's no repo (Intercom, Zendesk, Help Scout, Notion), write markdown locally for the founder to paste in, or create *drafts* through the platform's API when the founder asks.
- **Product code.** Every setting passes through three layers:
  - the screen where it's set (the frontend)
  - the code that validates and saves it (the backend)
  - the code that uses it (the page, widget, email or job the end customer sees)

  You need all three. A setting can save correctly and still do nothing if the third layer ignores it.
- **Browser account.** Find out which account the browser is signed in to, and its role: owner, admin or member. Find out which demo workspace you're allowed to change. If the only session is production, agree in writing on what you may touch.
- **Publishing policy.** By default, work on a new branch and stage your changes. Don't commit, push, merge or publish unless the founder asks. Published docs get indexed and scraped within hours, so they're hard to take back.
- **Scope and audience.** Is this the whole product or a few areas? Is it for end users, admins or developers?

## Four rules that matter most

**1. Only document behaviour you have verified.** A help page that promises something the product doesn't do creates support tickets and costs trust. Reading the code, you'll find things like these:

- settings that save but are never read
- options the UI offers that the backend rejects
- limits enforced in one place but not another
- labels that don't match what happens

Leave these out of the docs. Put each one in the internal bug report: what the user sees, the cause, and one code reference.

**2. The browser is real.** Claude in Chrome drives the founder's own signed-in browser, so every click is a real action.

- Work only in a demo workspace. Never change real customer or primary workspaces.
- Document destructive flows (delete, cancel, remove member, revoke key) on demo data. Stop at the confirmation dialog: screenshot it, then cancel.
- Before you change a demo setting, write down its current value. Keep a changelog of every change for the handoff.
- Prefer on-screen-only states. Toggle a setting to show its effect, capture it, then reload without saving.
- Never type passwords, payment details or real personal data. The founder signs in themselves.

**3. Nothing internal leaks.** Help pages contain only what a customer needs. Leave out all of these:

- names of internal services, databases, fields and feature flags
- code and file paths
- internal or staging hostnames
- endpoints that aren't for customers
- backend vendors the customer never deals with
- employee names and emails
- customer names
- unreleased features and non-public pricing

Describe behaviour, not implementation. Write "changes can take a few minutes to appear", not "the cache TTL is 300 seconds". This applies to screenshots too (step 7).

**4. Hand off, don't publish.** Your review preview and handoff note contain internal material, such as the bug list and code references. Keep them out of the docs repo and share them only with the founder.

## Workflow

### 1. Read the existing docs

- **Conventions.** Learn the page template, frontmatter, heading style, callout syntax, image markup, alt text, file naming, icon convention and tone. New pages should look like they were always there.
- **Coverage.** List what's already covered, so new pages link to it instead of repeating it.
- **Suspects.** Note pages that look out of date. You'll check them in step 9.

### 2. Inventory the product from its code

Go area by area, following the product's own navigation: each settings tab, modal and menu. For every control, record these fields:

| Field | Example |
| --- | --- |
| Exact UI label | "Send reminder emails" |
| Where it is | Settings → Notifications |
| What it does, traced to where it takes effect | Emails the client 3 days before an invoice is due |
| Default | On |
| Plan or role gating | Pro plan and above, admins only |
| Limits | Up to 5 reminders; subject line up to 120 characters |
| Depends on | Only shown when **Email notifications** is on |
| Edge cases | Downgrade, delete, empty state, what happens to existing data |
| Verified? | Read end to end, or assumed |
| Code reference | Internal only, for the bug report |

Also collect the questions customers really ask, from the support inbox, chat logs, docs search terms and sales calls if the founder can share them. Most pages follow one of four patterns:

- "How do I turn off X"
- "Why isn't Y showing"
- "What's the limit on Z"
- "What happens if I cancel"

Save one inventory file per area in a scratch folder **outside** the docs repo, because they contain code references.

### 3. Plan the pages

- **One question per page.** Short, single-answer pages get found by search and AI assistants, and they're easy to keep current.
- **Self-explanatory titles.** Write the question in the customer's words, specific enough to stand alone in a search result or sidebar. Name both the thing and the place.
  - Weak: "Reminders", "Dark mode", "Limits".
  - Strong: "How to turn off reminder emails for overdue invoices", "How to switch the client portal to dark mode", "How many team members each plan includes".
  - Useful patterns: "How to [task] [where]", "Why [symptom] and how to fix it", "What counts as [thing]", "[A] vs [B]: which one to use".
- **Troubleshooting pages.** Add a page for each common symptom, such as "not showing on my site" or "changes not appearing".
- **Grouping.** Group pages the way the product's navigation is grouped, with one folder per group and kebab-case file names taken from the title.
- **Share the plan.** If there are more than about 20 pages, show the founder the list of titles first. Fixing titles is cheap before the pages exist.

### 4. Write the pages

Use this template, in the platform's syntax (see `references/platforms.md`):

```markdown
---
description: One or two sentences on what this page answers. Used for search snippets and link previews.
---

# How to turn off reminder emails for overdue invoices

The answer first, in one or two sentences: where the setting is and what it does.

(Callout: plan or role requirement, if any.)

## Steps

1. Open **Settings** and click **Notifications**.
2. Turn off **Send reminder emails**.
3. Click **Save**.

(Annotated screenshot. Its numbered badges match the step numbers. The caption states the takeaway.)

## Good to know

* Defaults, limits, what it interacts with, what happens on downgrade or cancel, and how fast changes appear.

## Related

* Two to four links to related pages.
```

Follow these writing rules:

- Put exact UI labels in **bold**, spelled and capitalised exactly as the product shows them.
- Use second person, present tense and short sentences.
- Answer first, with no preamble such as "In this article we will...".
- Write numbers as digits, with exact limits and units.
- Cover edge cases: downgrade, cancel, delete, empty states.
- For destructive actions, add a warning callout that says what's lost and whether it can be undone.
- Never promise future features.
- Match the existing pages' icon convention. If existing pages have icons, give every new page its own distinct icon.

### 5. Capture annotated screenshots with Claude in Chrome

**Setup.** Claude in Chrome is Anthropic's browser extension. It lets Claude navigate, click, run JavaScript and take screenshots in your browser, using your existing sign-in.

- **Claude Code:** start Claude Code with `claude --chrome`, or run `/chrome` inside a session.
- **Requirements:** a paid Claude plan and a Chromium browser (Chrome, Edge, Brave and others).
- **Claude app:** it also works from claude.ai and the desktop app.

Take screenshots one at a time from the main agent. There's one browser, and parallel agents clicking in it collide.

For each screenshot:

1. **Prepare the state.** Use the demo workspace, with realistic fictional data such as an invented business, invented names, `@example.com` emails and a made-up logo. Random filler like "test 123" makes docs look unfinished. Use one window size for the whole set (about 1440×900) and resize the window if needed.
2. **Wait for the page to load.** Heavy dashboards can take a minute or two. Check for a known element or the tab title before deciding a page is stuck, and don't reload in a loop.
3. **Keep the window visible.** Captures of a minimized or hidden window can time out.
4. **Stage on-screen-only states** when a step needs them, such as a toggle turned on or a field filled in. For inputs controlled by React or Vue, use `anno.setValue` (it sets the value the way the framework expects). Never click Save outside the demo workspace.
5. **Hide sensitive text** before capturing: API keys, IDs and emails. Use `anno.swapText`, which puts in a same-length placeholder so the layout doesn't shift. Use `anno.mask` for a solid block and `anno.blur` for faces or incidental content.
6. **Annotate.** Inject `scripts/annotate.js` with the browser's JavaScript tool. Add a box around each control mentioned in the steps, numbered badges that match the step numbers, and a 1–4 word label or arrow when the target is small. Use no more than about 4 annotations per image.
7. **Move the mouse to an empty area**, so hover styles and tooltips don't show.
8. **Capture only the part that matters**, such as a panel or modal with a little context. Use the region (zoom) capture saved to disk: it keeps full sharpness, while a full-window screenshot gets scaled down.
9. **Clean up.** Run `anno.clear()`, then reload so every on-screen-only change is undone.

Name files `<group>-<topic>.png`, and never use one file for two different screens. Alt text says what the image shows; the caption says what to take from it.

**Gotchas**

- **Browser dialogs** (alert, confirm, "Leave site?") block the extension until a person dismisses them. Before leaving a screen with unsaved on-screen changes, reload it or undo the changes. If the app asks before leaving through `window.confirm`, replace that function with one that returns true for the session.
- **Hidden duplicates.** Responsive apps often render two copies of an element, one hidden. `annotate.js` picks the visible one. If a box lands in the wrong place, check `anno.find('Label')`.
- **Account roles.** A member session can't see owner-only screens, such as billing, team management or ownership transfer. Signed-out screens (login, sign-up, password reset) need a signed-out window. Don't fake these screens. List them for the founder with the exact state to capture and the target file name.
- **Built-in content** can show real people, even in a demo workspace: template galleries, sample avatars, stock photos, "recent activity" strips, and AI summaries that quote real data. Check for these before you capture.

### 6. Check every page against the live product

While you take the screenshots, follow every step of every page in the real UI. Compare:

- button labels and the order of the steps
- when a control appears (plan, role, other settings)
- what the result looks like

Drafts written only from code are often wrong about conditional UI. Fix each page, and list the notable corrections in the handoff.

### 7. Privacy audit

**Text.** Run `python scripts/privacy_scan.py <docs-dir> --deny internal-terms.txt`. The terms file lists internal service names, database names, internal hosts, vendor names, staff names and customer names, and it lives outside the repo. Review every hit, then read the pages once more for anything a customer wouldn't need.

**Images.** Look at every image yourself, or with a vision subagent for each batch of about 20. Check for:

- real names, emails, faces and customer content
- other companies' logos
- IDs, keys and tokens
- internal URLs and amounts
- workspace switchers that list other accounts
- notification counts
- AI output that quotes real data
- built-in sample content showing real people

The same script with `--images` reports hidden metadata in images (PNG text chunks, JPEG EXIF). `--strip` removes it.

**Fixes, best first:**

1. **Retake** with demo data or an `anno.swapText` placeholder.
2. **For secrets** (keys, tokens, IDs), use a solid block. Blurred or pixelated text can sometimes be recovered.
3. **For incidental content** (a face, a strip of someone's text), use a heavy blur shaped to the element. Use `scripts/redact.py` for images you've already captured. It keeps the untouched originals in a folder you choose, so you can re-run it. Keep that folder out of the repo.

In the handoff, list what you fixed and what you left for the founder to decide. An example of the second: a third-party logo that's already on their marketing site.

### 8. Check links, images and the table of contents

Run `python scripts/check_docs.py <docs-root> --toc <SUMMARY.md|docs.json>`, and add `--external` to also test outside links. It checks that:

- every relative link and image resolves
- every image has alt text
- no new image is orphaned
- every new page appears in the table of contents exactly once

### 9. Audit the existing pages

Compare existing pages that overlap your new ones with the code and the live UI. Look for renamed buttons, changed limits, removed options, and contradictions with the new pages. Report them in a table with three columns: page, what's wrong, what's true now. Don't rewrite existing pages unless the founder asks. Keeping the change set additive makes it easy to review.

### 10. Build the review preview and hand off

**Preview.** If the platform can preview a branch, use that (see `references/platforms.md`). If it can't, or the target is a hosted help center, run `python scripts/build_review.py <docs-root> --pages <new pages...> --overview handoff.md --out <scratch>/review`. That builds a static HTML page showing every new page with its images. Use a CommonMark renderer (the script uses markdown-it-py). Some other markdown libraries lose nested lists indented by 3 spaces.

**Handoff note**, in this order:

1. **Where the work is:** the repo, the branch, what changed with counts, and its state (staged, not pushed).
2. **How to publish:** the exact steps for their platform.
3. **Privacy check:** the text scan, the metadata check, the images you fixed, and what's left for their call.
4. **How the pages were checked:** against the code and against the live UI.
5. **Screenshots only they can take:** a table with the page, what to capture, the file name and what to blur.
6. **Corrections found during the live check.**
7. **Changes made in the demo account:** each one, and how to undo it.
8. **Existing pages that are now wrong.**
9. **Bugs found:** what the user sees, the cause and a code reference, ranked by customer impact. This part is internal.

## Working in parallel

Subagents are a good fit for work that only reads or writes files:

- one inventory agent per product area
- one drafting agent per page group, working from the inventories
- an independent agent that checks each drafted page's claims against the code
- one image-audit agent per batch
- the stale-page audit

Give every agent the four rules above and the page template. Keep all browser work in the main agent.

## Bundled files

- `scripts/annotate.js`: overlay helper for the browser. Read it and pass its full contents to the JavaScript tool once per page load; route changes inside a single-page app keep it. The API is listed at the top of the file.
- `scripts/privacy_scan.py`: text scan (emails, IDs, key and token shapes, internal hosts, infrastructure URLs, code paths, your terms list) and image metadata report/strip. Uses only the Python standard library.
- `scripts/check_docs.py`: link, image, alt-text and table-of-contents checks. Uses only the Python standard library.
- `scripts/redact.py`: blur, fill or circle-blur regions of captured images, keeping the originals. Needs `pip install pillow`.
- `scripts/build_review.py`: static HTML review preview. Needs `pip install markdown-it-py`.
- `references/platforms.md`: table-of-contents files, callouts, images, icons, previews and publishing for each docs platform.

If the scripts aren't available, do the same checks by hand. The steps above describe what each one looks for.
