import { type IconName } from "@blueprintjs/icons";
import { type HTMLDivProps, Intent, type IntentProps, type MaybeElement, type Props } from "../../common";
/** This component also supports the full range of HTML `<div>` attributes. */
export interface CalloutProps extends IntentProps, Props, HTMLDivProps {
    /** Callout contents. */
    children?: React.ReactNode;
    /**
     * Whether to use a compact appearance, which reduces the visual padding around callout content.
     */
    compact?: boolean;
    /**
     * Name of a Blueprint UI icon (or an icon element) to render on the left side.
     *
     * If this prop is omitted or `undefined`, the `intent` prop will determine a default icon.
     * If this prop is explicitly `null`, no icon will be displayed (regardless of `intent`).
     */
    icon?: IconName | MaybeElement;
    /**
     * Visual intent color to apply to background, title, and icon.
     *
     * Defining this prop also applies a default icon, if the `icon` prop is omitted.
     */
    intent?: Intent;
    /**
     * Whether the callout should have a minimal appearance with no background color fill.
     *
     * @default false
     */
    minimal?: boolean;
    /**
     * String content of optional title element.
     *
     * Due to a conflict with the HTML prop types, to provide JSX content simply
     * pass `<H4>JSX title content</H4>` as first `children` element instead of
     * using this prop (note uppercase tag name to use the Blueprint Heading
     * component).
     */
    title?: string;
}
/**
 * Callout component.
 *
 * @see https://blueprintjs.com/docs/#core/components/callout
 */
export declare const Callout: React.FC<CalloutProps>;
