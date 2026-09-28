# help-center-builder

A [Claude Code](https://code.claude.com) skill that builds or extends your product's help center straight from your own codebase, with annotated screenshots of your live app.

Most help centers cover the big topics and skip the small questions customers actually ask, like "How do I turn off reminder emails?" or "Why isn't my change showing?". This skill works through your product setting by setting and writes one clear, searchable page for each question. You review everything before it goes live.

## What it does

1. **Learns your stack.** On the first run it asks about your docs platform, how you publish, where your code lives and which demo account to use. It saves the answers so later runs skip the questions.
2. **Lists every setting from your code.** It traces each setting from the screen where it's set, through the code that saves it, to the part your customers see. A setting that saves but does nothing goes into a bug report, not into your docs.
3. **Plans the pages.** Each page answers one question, with a title in your customers' words ("How to turn off reminder emails for overdue invoices", not "Reminders").
4. **Writes each page from one template.** The answer comes first, then the steps, "Good to know" notes and related links, in your platform's own syntax.
5. **Takes annotated screenshots** with [Claude in Chrome](https://code.claude.com/docs/en/chrome), on a demo account with realistic fictional data. Red boxes and numbered badges match the step numbers in the text.
6. **Checks every page against the live product.** Drafts written only from code are often wrong about buttons and conditions.
7. **Runs a privacy check.** It scans the text for internal names, hosts, keys and code, and checks every image for personal data, secrets and hidden metadata.
8. **Checks links, images and your table of contents.**
9. **Lists existing pages that are now out of date.**
10. **Hands off for review.** You get a branch, a preview of every page and a handoff note. It never publishes for you.

## Supported docs platforms

GitBook, Mintlify, Docusaurus, Nextra and ReadMe (docs in a git repo), plus Intercom, Zendesk, Help Scout and Notion (hosted help centers). For hosted help centers it writes pages for you to paste in, or creates unpublished drafts through their API when you ask.

## Install

Copy this folder into your Claude Code skills folder:

```bash
# for all your projects
git clone https://github.com/<you>/help-center-builder ~/.claude/skills/help-center-builder

# or for one project only
git clone https://github.com/<you>/help-center-builder .claude/skills/help-center-builder
```

Then ask Claude Code something like:

> Our help docs miss the small how-to questions. Go through the app's settings and write help pages with annotated screenshots.

Claude picks up the skill on its own. You can also run it directly with `/help-center-builder`.

## Requirements

- **Claude Code.**
- **Screenshots:** [Claude in Chrome](https://code.claude.com/docs/en/chrome), which needs a paid Claude plan and Chrome, Edge or another Chromium browser. Start Claude Code with `claude --chrome`, or run `/chrome` in a session. Without it, the skill still writes the pages and lists the screenshots for you to take.
- **Python 3.8+** for the helper scripts. Two scripts need an extra package: `pip install pillow markdown-it-py`.

## What's inside

| File | What it's for |
| --- | --- |
| `SKILL.md` | The step-by-step method Claude follows |
| `references/platforms.md` | Table of contents, callouts, images, icons, previews and publishing for each platform |
| `scripts/annotate.js` | Browser overlay for boxes, numbered badges, labels and arrows, plus on-screen-only blur and masking for secrets |
| `scripts/privacy_scan.py` | Flags emails, IDs, keys, internal hosts, code paths and your own list of private terms; finds and strips image metadata |
| `scripts/check_docs.py` | Finds broken links, missing images, missing alt text, unused images and pages missing from the table of contents |
| `scripts/redact.py` | Blurs or blocks out parts of screenshots you've already taken, keeping the originals |
| `scripts/build_review.py` | Builds one HTML page showing every new page, so you can review before publishing |

You can also run the scripts on their own. Use `--help` on any of them for usage.

## Safety

Claude in Chrome uses your real, signed-in browser, so the skill is built to be careful:

- It works only in a demo workspace you name. It stops at confirmation dialogs for destructive actions and keeps a log of every change it makes there.
- It never types passwords or payment details. You sign in yourself.
- It never commits, pushes or publishes unless you ask.
- Internal material stays out of your docs repo. That includes the bug report, the code references and the setup file.

Still review the changes before you merge, as you would with any pull request.
