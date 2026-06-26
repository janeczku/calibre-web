import { type ActionProps } from "../../common/props";
import type { PopoverProps } from "../popover/popoverProps";
import { type MenuProps } from "./menu";
/**
 * Note that the HTML attributes supported by this component are spread to the nested `<a>` element, while the
 * `ref` is attached to the root `<li>` element. This is an unfortunate quirk in the API which we keep around
 * for backwards-compatibility.
 */
export interface MenuItemProps extends ActionProps<HTMLAnchorElement>, React.AnchorHTMLAttributes<HTMLAnchorElement>, React.RefAttributes<HTMLLIElement> {
    /** Item text, required for usability. */
    text: React.ReactNode;
    /**
     * Whether this item should appear _active_, often useful to
     * indicate keyboard focus. Note that this is distinct from _selected_
     * appearance, which has its own prop.
     */
    active?: boolean;
    /**
     * Children of this component will be rendered in a _submenu_
     * that appears in a popover when hovering or clicking on this item.
     *
     * Use `text` prop for the content of the menu item itself.
     */
    children?: React.ReactNode;
    /**
     * Whether this menu item is non-interactive. Enabling this prop will ignore `href`, `tabIndex`,
     * and mouse event handlers (in particular click, down, enter, leave).
     */
    disabled?: boolean;
    /**
     * Right-aligned label text content, useful for displaying hotkeys.
     *
     * This prop actually supports JSX elements, but TypeScript will throw an error because
     * `HTMLAttributes` only allows strings. Use `labelElement` to supply a JSX element in TypeScript.
     */
    label?: string;
    /**
     * A space-delimited list of class names to pass along to the right-aligned label wrapper element.
     */
    labelClassName?: string;
    /**
     * Right-aligned label content, useful for displaying hotkeys.
     */
    labelElement?: React.ReactNode;
    /**
     * Changes the ARIA `role` property structure of this MenuItem to accomodate for various
     * different `role`s of the parent Menu `ul` element.
     *
     * If `menuitem`, role structure becomes:
     *
     * `<li role="none"><a role="menuitem" /></li>`
     *
     * which is proper role structure for a `<ul role="menu"` parent (this is the default `role` of a `Menu`).
     *
     * If `listoption`, role structure becomes:
     *
     * `<li role="option"><a role={undefined} /></li>`
     *
     * which is proper role structure for a `<ul role="listbox"` parent, or a `<select>` parent.
     *
     * If `listitem`, role structure becomes:
     *
     * `<li role={undefined}><a role={undefined} /></li>`
     *
     * which can be used if this item is within a basic `<ul/>` (or `role="list"`) parent.
     *
     * If `none`, role structure becomes:
     *
     * `<li role="none"><a role={undefined} /></li>`
     *
     * which can be used if wrapping this item in a custom `<li>` parent.
     *
     * @default "menuitem"
     */
    roleStructure?: "menuitem" | "listoption" | "listitem" | "none";
    /**
     * Whether the text should be allowed to wrap to multiple lines.
     * If `false`, text will be truncated with an ellipsis when it reaches `max-width`.
     *
     * @default false
     */
    multiline?: boolean;
    /**
     * Props to spread to the submenu popover. Note that `content` and `minimal` cannot be
     * changed and `usePortal` defaults to `false` so all submenus will live in
     * the same container.
     */
    popoverProps?: Partial<Omit<PopoverProps, "content" | "minimal">>;
    /**
     * Whether this item should appear selected - `roleStructure` must be `"listoption"` for this to be
     * applied. Defining this will set the `aria-selected` attribute and apply a small tick icon if `true`,
     * and empty space for a small tick icon if `false` or `undefined`.
     *
     * @default undefined
     */
    selected?: boolean;
    /**
     * Whether an enabled item without a submenu should automatically close its parent popover when clicked.
     *
     * @default true
     */
    shouldDismissPopover?: boolean;
    /**
     * Props to spread to the child `Menu` component if this item has a submenu.
     */
    submenuProps?: Partial<MenuProps>;
    /**
     * Name of the HTML tag that wraps the MenuItem.
     *
     * @default "a"
     */
    tagName?: keyof React.JSX.IntrinsicElements;
    /**
     * A space-delimited list of class names to pass along to the text wrapper element.
     */
    textClassName?: string;
    /**
     * HTML title to be passed to the <Text> component
     */
    htmlTitle?: string;
}
/**
 * Menu item component.
 *
 * @see https://blueprintjs.com/docs/#core/components/menu.menu-item
 */
export declare const MenuItem: React.FC<MenuItemProps>;
