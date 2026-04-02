# LedgerLens 2 — Project Guidelines

## Frontend Aesthetics

You tend to converge toward generic, "on distribution" outputs. In frontend design, this creates what users call the "AI slop" aesthetic. Avoid this: make creative, distinctive frontends that surprise and delight. Focus on:

**Typography:** Choose fonts that are beautiful, unique, and interesting. Avoid generic fonts like Arial and Inter; opt instead for distinctive choices that elevate the frontend's aesthetics.

**Color & Theme:** Commit to a cohesive aesthetic. Use CSS variables for consistency. Dominant colors with sharp accents outperform timid, evenly-distributed palettes. Draw from IDE themes and cultural aesthetics for inspiration.

**Motion:** Use animations for effects and micro-interactions. Prioritize CSS-only solutions for HTML. Use Motion library for React when available. Focus on high-impact moments: one well-orchestrated page load with staggered reveals (animation-delay) creates more delight than scattered micro-interactions.

**Backgrounds:** Create atmosphere and depth rather than defaulting to solid colors. Layer CSS gradients, use geometric patterns, or add contextual effects that match the overall aesthetic.

**Avoid generic AI-generated aesthetics:**

- Overused font families (Inter, Roboto, Arial, system fonts)
- Cliched color schemes (particularly purple gradients on white backgrounds)
- Predictable layouts and component patterns
- Cookie-cutter design that lacks context-specific character

Interpret creatively and make unexpected choices that feel genuinely designed for the context. Vary between light and dark themes, different fonts, different aesthetics. Avoid converging on common choices (Space Grotesk, for example) across generations. Think outside the box.

## Architecture Documentation

- The file `architecture.md` is the **single source of truth** for LedgerLens 2’s architecture.
- Any architectural changes, updates, or discoveries **must** be reflected in `architecture.md` immediately.
- If you re-implement or refactor any part of the application, update `architecture.md` to match the current state.
- When in doubt, defer to `architecture.md` for all architectural, data model, and system design questions.
- If you find `architecture.md` is out of sync with the codebase, **update it first** before proceeding.
- All contributors and AI assistants are responsible for keeping this file accurate and current.
