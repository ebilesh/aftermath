---
name: Aftermath
description: A daylight engineering workbench for payment failure recovery.
colors:
  page: "#f6f7f3"
  rail: "#edf0e9"
  surface: "#ffffff"
  ink: "#23352e"
  primary: "#235e43"
  primary-hover: "#174a32"
  border: "#dce2d8"
  field: "#fafbf8"
  field-border: "#d6dfd3"
  focus: "#17694c"
  selected: "#dce7da"
  proof: "#edf4e9"
  proof-ink: "#315e39"
  fault: "#bd7c43"
  fault-ink: "#a06835"
  simulation: "#f1eadc"
  simulation-ink: "#856236"
  muted: "#6c786e"
typography:
  headline:
    fontFamily: '"DM Sans", sans-serif'
    fontSize: "36px"
    fontWeight: 550
    letterSpacing: "-1.2px"
  title:
    fontFamily: '"DM Sans", sans-serif'
    fontSize: "17px"
    fontWeight: 650
  body:
    fontFamily: '"DM Sans", sans-serif'
    fontSize: "14px"
    lineHeight: 1.6
  label:
    fontFamily: '"DM Sans", sans-serif'
    fontSize: "12px"
    fontWeight: 550
  identifier:
    fontFamily: monospace
    fontSize: "10px"
rounded:
  panel: "9px"
  control: "5px"
  badge: "4px"
  navigation: "6px"
spacing:
  panel: "23px"
  workspace-gap: "23px"
  main-inline: "42px"
  field-padding: "11px"
components:
  button-primary:
    backgroundColor: "{colors.primary}"
    textColor: "{colors.surface}"
    rounded: "{rounded.control}"
    padding: "13px 15px"
    width: "100%"
  button-primary-hover:
    backgroundColor: "{colors.primary-hover}"
  panel:
    backgroundColor: "{colors.surface}"
    rounded: "{rounded.panel}"
    padding: "{spacing.panel}"
  input:
    backgroundColor: "{colors.field}"
    rounded: "{rounded.control}"
    padding: "{spacing.field-padding}"
---

# Design System: Aftermath

## Overview

**Creative North Star: "Daylight engineering workbench"**

Quiet green neutrals, flat white panels, and compact typography support precise inspection. The interface puts recovery evidence close to the experiment controls and uses restrained color to distinguish faults from successful credit.

**Key Characteristics:**

- Compact, task-focused controls and evidence.
- Green correctness signals and amber fault signals.
- Visible distinction between simulated activity and read-only chain inspection.

This document records the implementation in `frontend/src/style.css` and `frontend/src/main.tsx`. It reflects source inspection only. Browser verification was blocked by sandbox EPERM.

## Colors

The palette combines warm daylight neutrals with a deep green action color. Primary green identifies actions and active navigation. Pale green grounds credit evidence and completion states. Amber marks simulated activity and crash events. Page, rail, and white surface tones establish hierarchy through contrast and borders.

## Typography

DM Sans is the interface family, with a generic sans-serif fallback. Monospace is reserved for run identifiers, logical ticks, transaction signatures, and raw RPC results. Headline and title roles follow the frontmatter. Run titles use 20px at weight 600; timeline text uses 11px, with descriptions limited to 65ch. Compact captions range from 9px to 12px.

## Layout

The desktop shell places a sticky 246px navigation rail beside a main workspace capped at 1600px. The main area has 42px horizontal padding, an 83px breadcrumb header, and an introduction above the working surfaces.

The Failure lab uses a 310px experiment setup column and a flexible recovery workbench, separated by 23px. The recovery workbench contains run identity and export, a four-step pipeline, credit evidence, and the event timeline with its advance or restart action. Recent experiments span the width below both panels. The separate transaction inspector uses one panel capped at 900px.

At widths of 1500px and above, main padding becomes 60px and setup becomes 340px. At 1100px and below, the rail narrows to 190px, main padding becomes 24px, setup narrows to 270px, and dense rows wrap. At 800px and below, the rail becomes a static top navigation strip, secondary rail content is hidden, main padding becomes 18px, and setup stacks above recovery. Saved experiments remain below; their descriptions wrap to another row. The footer stacks vertically.

## Elevation & Depth

No shadows are defined. Tonal layering and thin borders separate the page, rail, panels, fields, and evidence regions. The timeline uses small dots and a fine connecting rule to express event order.

## Shapes

Panels use the panel radius. Inputs and primary controls use the control radius, compact status labels use the badge radius, and navigation buttons use the navigation radius. Panels have a one-pixel border. Status and timeline markers are circular.

## Components

Primary buttons fill the setup width and use a darker green on hover. Timeline actions use a compact pale-green outlined treatment. Export uses an outlined icon button with an accessible name. All buttons, links, inputs, and selects receive a two-pixel green focus outline with a four-pixel offset. Disabled buttons use 0.45 opacity and a not-allowed cursor.

Fields pair visible labels with compact inputs or selects. Number inputs sit beside explanatory text. Navigation uses icon-and-label buttons and a pale-green active background. Saved-run rows use top dividers and a pale hover or selected fill.

Credit evidence uses a pale-green inset region with a shield icon, credit count, invariant statement, and acknowledgement count. The timeline is the primary recovery evidence; it scrolls vertically after 430px. Crash events use amber dots and labels, while credit events use green dots. Empty, stopped, ready, and complete states use explicit text. Inspector errors appear in an alert region above the active surface.

Buttons transition background over 150ms with the CSS default easing. Reduced-motion preferences disable transitions.

## Do's and Don'ts

- Do retain visible simulation and read-only labels.
- Do keep identifiers and logical ticks in monospace.
- Do preserve keyboard focus outlines and reduced-motion behavior.
- Do keep setup before recovery in mobile reading order.
- Don't use shadows to add hierarchy to the existing flat surfaces.
- Don't let the pipeline replace the event timeline as recovery evidence.
