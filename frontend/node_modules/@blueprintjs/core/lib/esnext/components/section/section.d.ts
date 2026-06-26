import { type IconName } from "@blueprintjs/icons";
import { Elevation } from "../../common";
import { type HTMLDivProps, type MaybeElement, type Props } from "../../common/props";
import { type CollapseProps } from "../collapse/collapse";
/**
 * Subset of {@link Elevation} options which are visually supported by the {@link Section} component.
 *
 * Note that an elevation greater than 1 creates too much visual clutter/noise in the UI, especially when
 * multiple Sections are shown on a single page.
 */
export type SectionElevation = typeof Elevation.ZERO | typeof Elevation.ONE;
export interface SectionCollapseProps extends Pick<CollapseProps, "className" | "isOpen" | "keepChildrenMounted" | "transitionDuration"> {
    /**
     * Whether the component is initially open or closed.
     *
     * This prop has no effect if `collapsible={false}` or the component is in controlled mode,
     * i.e. when `isOpen` is **not** `undefined`.
     *
     * @default true
     */
    defaultIsOpen?: boolean;
    /**
     * Whether the component is open or closed.
     *
     * Passing a boolean value to `isOpen` will enabled controlled mode for the component.
     */
    isOpen?: boolean;
    /**
     * Callback invoked in controlled mode when the collapse toggle element is clicked.
     */
    onToggle?: () => void;
}
export interface SectionProps extends Props, Omit<HTMLDivProps, "title">, React.RefAttributes<HTMLDivElement> {
    /**
     * Whether this section's contents should be collapsible.
     *
     * @default false
     */
    collapsible?: boolean;
    /**
     * Subset of props to forward to the underlying {@link Collapse} component, with the addition of a
     * `defaultIsOpen` option which sets the default open state of the component when in uncontrolled mode.
     */
    collapseProps?: SectionCollapseProps;
    /**
     * Whether this section should use compact styles.
     *
     * @default false
     */
    compact?: boolean;
    /**
     * Visual elevation of this container element.
     *
     * @default Elevation.ZERO
     */
    elevation?: SectionElevation;
    /**
     * Name of a Blueprint UI icon (or an icon element) to render in the section's header.
     * Note that the header will only be rendered if `title` is provided.
     */
    icon?: IconName | MaybeElement;
    /**
     * Element to render on the right side of the section header.
     * Note that the header will only be rendered if `title` is provided.
     */
    rightElement?: React.JSX.Element;
    /**
     * Sub-title of the section.
     * Note that the header will only be rendered if `title` is provided.
     */
    subtitle?: React.JSX.Element | string;
    /**
     * Title of the section.
     * Note that the header will only be rendered if `title` is provided.
     */
    title?: React.JSX.Element | string;
    /**
     * Optional title renderer function. If provided, it is recommended to include a Blueprint `<H6>` element
     * as part of the title. The render function is supplied with `className` and `id` attributes which you must
     * forward to the DOM. The `title` prop is also passed along to this renderer via `props.children`.
     *
     * @default H6
     */
    titleRenderer?: React.FC<React.HTMLAttributes<HTMLElement>>;
}
/**
 * Section component.
 *
 * @see https://blueprintjs.com/docs/#core/components/section
 */
export declare const Section: React.FC<SectionProps>;
