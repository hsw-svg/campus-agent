# Responsive Motion Panels

## Scope

Use this contract for a panel that is an in-flow sidebar at a desktop breakpoint and a fixed drawer or sheet on narrow screens, especially when its content uses Motion `layoutId` animations.

## Single-Instance Contract

- Mount the panel content exactly once. Use responsive positioning classes on one shell instead of rendering separate desktop and mobile copies and hiding one with CSS.
- CSS-hidden React trees are still mounted. Their effects, local state, scroll containers, and Motion shared-layout nodes remain active.
- Keep the responsive shell responsible for placement and entry/exit motion; keep the content component responsible for content state only.

```tsx
// Correct: one content instance, two responsive placements.
<motion.div className="fixed inset-0 xl:relative xl:inset-auto xl:w-96">
  <button className="absolute inset-0 xl:hidden" onClick={onClose} />
  <motion.aside className="absolute right-0 h-full xl:relative">
    <PanelContent />
  </motion.aside>
</motion.div>
```

```tsx
// Wrong: both PanelContent trees mount and can collide even when one is hidden.
<aside className="hidden xl:block"><PanelContent /></aside>
<div className="xl:hidden"><PanelContent /></div>
```

## Shared-Layout Contract

- Every reusable component that declares a `layoutId` must scope it with `LayoutGroup` and an instance-specific React `useId()` value.
- The animated background stays absolutely positioned below icon and label content; icons keep explicit dimensions and `shrink-0`.
- Do not put a second entry translation on the inner content when the responsive shell already animates into view.

```tsx
const layoutGroupId = useId()

<LayoutGroup id={layoutGroupId}>
  {items.map((item) => (
    <button key={item.id}>
      {selected === item.id && <motion.span layoutId="active-item" />}
      <Icon className="h-4 w-4 shrink-0" />
    </button>
  ))}
</LayoutGroup>
```

## Stable-Width Scrolling

- A fixed-width panel has exactly one vertical scroll owner. Intermediate wrappers use `min-h-0 flex-1 overflow-hidden`.
- The scroll owner uses `overflow-y-auto` and `[scrollbar-gutter:stable]` so content width does not change when a scrollbar appears.
- All grid and flex descendants that may shrink use `min-w-0`; fixed icons use `shrink-0`.

## Required Checks

- At each responsive mode, opening the panel yields one content instance and one active shared-layout node.
- Switching every tab does not change the panel or navigation-grid width.
- Empty, long, and conditionally expanded content produces one vertical scrollbar at most.
- Reduced-motion mode removes large translation while retaining a short opacity transition.
- Run the frontend type check, production build, and `git diff --check` after changes.

## Common Failure

**Symptom:** one tab icon or selected background is missing on first open and returns after clicking; content width shifts after switching tabs.

**Cause:** responsive copies are mounted simultaneously with the same `layoutId`, while nested `overflow-y-auto` containers add or remove competing scrollbar gutters.

**Prevention:** use one responsive content instance, instance-scope `layoutId`, and assign scrolling to one stable-gutter container.
