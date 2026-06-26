import { AbstractPureComponent, type IntentProps } from "../../common";
import type { PopoverInteractionKind } from "../popover/popoverProps";
import type { DefaultPopoverTargetHTMLProps, PopoverSharedProps } from "../popover/popoverSharedProps";
export interface TooltipProps<TProps extends DefaultPopoverTargetHTMLProps = DefaultPopoverTargetHTMLProps> extends Omit<PopoverSharedProps<TProps>, "shouldReturnFocusOnClose">, IntentProps {
    /**
     * The content that will be displayed inside of the tooltip.
     */
    content: React.JSX.Element | string;
    /**
     * Whether to use a compact appearance, which reduces the visual padding around
     * tooltip content.
     *
     * @default false
     */
    compact?: boolean;
    /**
     * The amount of time in milliseconds the tooltip should remain open after
     * the user hovers off the trigger. The timer is canceled if the user mouses
     * over the target before it expires.
     *
     * @default 0
     */
    hoverCloseDelay?: number;
    /**
     * The amount of time in milliseconds the tooltip should wait before opening
     * after the user hovers over the trigger. The timer is canceled if the user
     * mouses away from the target before it expires.
     *
     * @default 100
     */
    hoverOpenDelay?: number;
    /**
     * The kind of hover interaction that triggers the display of the tooltip.
     * Tooltips do not support click interactions.
     *
     * @default PopoverInteractionKind.HOVER_TARGET_ONLY
     */
    interactionKind?: typeof PopoverInteractionKind.HOVER | typeof PopoverInteractionKind.HOVER_TARGET_ONLY;
    /**
     * Indicates how long (in milliseconds) the tooltip's appear/disappear
     * transition takes. This is used by React `CSSTransition` to know when a
     * transition completes and must match the duration of the animation in CSS.
     * Only set this prop if you override Blueprint's default transitions with
     * new transitions of a different length.
     *
     * @default 100
     */
    transitionDuration?: number;
}
/**
 * Tooltip component.
 *
 * @see https://blueprintjs.com/docs/#core/components/tooltip
 */
export declare class Tooltip<T extends DefaultPopoverTargetHTMLProps = DefaultPopoverTargetHTMLProps> extends AbstractPureComponent<TooltipProps<T>> {
    static displayName: string;
    static defaultProps: Partial<TooltipProps>;
    private popoverRef;
    render(): import("react/jsx-runtime").JSX.Element;
    reposition(): void;
    private renderPopover;
}
