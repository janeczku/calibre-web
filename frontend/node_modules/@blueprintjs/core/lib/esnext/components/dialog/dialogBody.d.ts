import type { HTMLDivProps, Props } from "../../common/props";
export interface DialogBodyProps extends Props, HTMLDivProps {
    /** Dialog body contents. */
    children?: React.ReactNode;
    /**
     * Enable scrolling for the container
     *
     * @default true
     */
    useOverflowScrollContainer?: boolean;
}
/**
 * Dialog body component.
 *
 * @see https://blueprintjs.com/docs/#core/components/dialog.dialog-body-props
 */
export declare const DialogBody: import("react").ForwardRefExoticComponent<DialogBodyProps & import("react").RefAttributes<HTMLDivElement>>;
