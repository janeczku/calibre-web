import type { HTMLDivProps, Props } from "../../common/props";
export interface DialogFooterProps extends Props, HTMLDivProps {
    /** Dialog actions (typically buttons) are rendered on the right side of the footer. */
    actions?: React.ReactNode;
    /** Child contents are rendered on the left side of the footer. */
    children?: React.ReactNode;
    /**
     * Use a "minimal" appearance for the footer, simply applying an HTML role and
     * some visual padding. This is useful for small dialogs, and should not be used
     * with `<DialogBody useOverflowScrollContainer>`.
     *
     * Note that this is the default behavior when using the CSS API, since that's
     * how the `-dialog-footer` class was first introduced, so these styles are
     * applied without a "modifier" class.
     *
     * When using the JS component API, `minimal` is false by default.
     *
     * Show the footer close from the content.
     * Do not use with scroll body
     * Use for small dialogs (confirm)
     *
     * @default false;
     */
    minimal?: boolean;
}
/**
 * Dialog footer component.
 *
 * @see https://blueprintjs.com/docs/#core/components/dialog.dialog-footer-props
 */
export declare const DialogFooter: import("react").ForwardRefExoticComponent<DialogFooterProps & import("react").RefAttributes<HTMLDivElement>>;
