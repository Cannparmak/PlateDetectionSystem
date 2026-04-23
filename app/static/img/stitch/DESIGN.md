# Design System Specification: The Nocturnal Architect

## 1. Overview & Creative North Star
**Creative North Star: "Precision in the Shadows"**

This design system moves away from the "generic SaaS dashboard" by embracing a high-contrast, editorial aesthetic inspired by technical excellence. The goal is not just to display data, but to curate it. By utilizing deep tonal layering and eliminating the "crutch" of traditional borders, we create an environment that feels like a high-end command center—authoritative, silent, and incredibly fast.

We break the "template" look through **intentional asymmetry** and **tonal depth**. The interface should feel less like a website and more like a custom-machined tool, where every pixel is a deliberate choice.

---

### 2. Colors & Surface Philosophy
The palette is built on the concept of "Obsidian Depth." We avoid flat black in favor of deep, cool-toned charcoals that allow for nuanced layering.

#### The "No-Line" Rule
**Explicit Instruction:** You are prohibited from using 1px solid borders for sectioning. Boundaries must be defined solely through background color shifts or subtle tonal transitions.
- Use `surface-container-low` for large section backgrounds.
- Use `surface-container` or `surface-container-high` for interactive cards.
- Contrast is your divider; whitespace is your structural support.

#### Surface Hierarchy & Nesting
Treat the UI as a physical stack of materials. 
- **Base Level:** `surface` (#111319) - The foundation.
- **Structural Sections:** `surface-container-low` (#191b22) - Sidebars or global navigation zones.
- **Actionable Layers:** `surface-container` (#1e1f26) - Primary dashboard cards.
- **Promoted Content:** `surface-container-highest` (#33343b) - Modals or popovers.

#### The "Glass & Gradient" Rule
To inject "soul" into the professional gray-scale:
- **Glassmorphism:** For floating elements (tooltips, dropdowns), use `surface-variant` at 70% opacity with a `24px` backdrop-blur.
- **The Signature Glow:** Active states should utilize a subtle `0px 0px 20px` outer glow using `primary-container` (#4d8eff) at 30% opacity to mimic the luminescence of high-end hardware.

---

### 3. Typography
We utilize the **Geist** font family for its mathematical precision and technical soul.

| Level | Token | Size | Weight | Use Case |
| :--- | :--- | :--- | :--- | :--- |
| **Display** | `display-lg` | 3.5rem | 700 | Massive KPI numbers, Hero stats |
| **Headline** | `headline-md` | 1.75rem | 600 | Page titles, major section headers |
| **Title** | `title-md` | 1.125rem | 500 | Card titles, modal headers |
| **Body** | `body-md` | 0.875rem | 400 | General UI text, data tables |
| **Label** | `label-sm` | 0.6875rem | 600 | Overline text, micro-labels (All Caps) |

**Editorial Note:** Use `label-sm` with 0.05em letter-spacing for metadata to create an "instrument panel" feel.

---

### 4. Elevation & Depth
In this design system, shadows are light, and layers are logic.

- **The Layering Principle:** Place a `surface-container-lowest` card (#0c0e14) onto a `surface-container-low` (#191b22) background to create "inset" depth for data inputs.
- **Ambient Shadows:** For floating elements, use a "No-Black Shadow." Use `on-surface` (#e2e2eb) at 4% opacity with a `40px` blur. This creates a natural "lift" rather than a dirty smudge.
- **The "Ghost Border":** If a visual separator is mandatory for accessibility, use `outline-variant` (#424754) at **15% opacity**. It should be felt, not seen.

---

### 5. Components

#### Buttons
- **Primary:** Background `primary` (#adc6ff), Text `on-primary` (#002e6a). Solid color, but with a subtle top-to-bottom 5% brightness gradient to avoid "flatness." Corner radius: `md` (12px).
- **Secondary:** Background `secondary-container` (#42474f), Text `on-secondary`. 
- **The "Active" State:** Every primary button interaction triggers the "Signature Glow" (Primary accent blue at 40% blur).

#### Cards & Lists
- **Rule:** Absolute prohibition of divider lines.
- **Implementation:** Separate list items using an 8px vertical gap. Use a subtle hover state change to `surface-container-highest` to indicate interactivity.
- **The Parking Grid:** For parking slot visualizations, use `surface-container-lowest` for empty spots and `tertiary-container` (#00a572) for occupied, creating a glowing "active" grid.

#### Input Fields
- **Default:** `surface-container-low` with a `Ghost Border` (15% opacity).
- **Focus:** Border transitions to `primary` at 50% opacity with a `4px` blue outer glow.
- **Typography:** Placeholder text must use `on-surface-variant` (#c2c6d6).

#### Signature Component: "The Occupancy Gauge"
A custom component for OtoparkPro. Use a thick, semi-circular stroke using `surface-variant` as the track and a `primary` to `tertiary` gradient for the fill. No text labels; just a large `display-lg` percentage in the center.

---

### 6. Do's and Don'ts

#### Do
- **Do** use `8px` increments for all spacing. Consistency is the only way to make "No-Line" layouts work.
- **Do** use `Geist Mono` for numerical data and license plate numbers to emphasize the technical nature of the software.
- **Do** lean into asymmetry. A left-aligned header with a right-aligned, floating "Status" pill creates a modern, editorial rhythm.

#### Don't
- **Don't** use pure black (#000000). It kills the "depth" and makes the UI feel like a 90s terminal.
- **Don't** use standard shadows. If the shadow looks like a "shadow," it's too dark.
- **Don't** use more than one primary button per view. The high-contrast blue is a powerful tool; don't dilute its meaning.
- **Don't** use 100% opaque borders. They create visual noise that distracts from the data.