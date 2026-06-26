import { type IconName } from "@blueprintjs/icons";
import { type MaybeElement, type Props } from "../../common";
import type { BackdropProps, OverlayableProps } from "../overlay/overlayProps";
export interface DialogProps extends OverlayableProps, BackdropProps, Props {
    /** Dialog contents. */
    children?: React.ReactNode;
    /**
     * Ref attached to the `Classes.DIALOG_CONTAINER` element.
     */
    containerRef?: React.Ref<HTMLDivElement>;
    /**
     * Toggles the visibility of the overlay and its children.
     * This prop is required because the component is controlled.
     *
     * @default false
     */
    isOpen?: boolean;
    /**
     * Dialog always has a backdrop so this prop cannot be overriden.
     */
    hasBackdrop?: never;
    /**
     * Name of a Blueprint UI icon (or an icon element) to render in the
     * dialog's header. Note that the header will only be rendered if `title` is
     * not null or undefined.
     */
    icon?: IconName | MaybeElement;
    /**
     * Whether to show the close button in the dialog's header.
     * Note that the header will only be rendered if `title` is not null or undefined.
     *
     * @default true
     */
    isCloseButtonShown?: boolean;
    /**
     * @default "dialog"
     */
    role?: Extract<React.AriaRole, "dialog" | "alertdialog">;
    /**
     * CSS styles to apply to the dialog.
     *
     * @default {}
     */
    style?: React.CSSProperties;
    /**
     * Title of the dialog. If not null or undefined, an element with `Classes.DIALOG_HEADER`
     * will be rendered inside the dialog before any children elements.
     * An empty string `""` will render the header without a visible title (useful for
     * showing the close button without a title).
     */
    title?: React.ReactNode;
    /**
     * HTML heading component to use for the dialog title.
     *
     * @default H2
     */
    titleTagName?: React.ElementType<React.HTMLAttributes<HTMLElement>>;
    /**
     * Name of the transition for internal `CSSTransition`. Providing your own
     * name here will require defining new CSS transition properties.
     */
    transitionName?: string;
    /**
     * ID of the element that contains title or label text for this dialog.
     *
     * By default, if the `title` prop is supplied, this component will generate
     * a unique ID for the `<H5>` title element and use that ID here.
     */
    "aria-labelledby"?: string;
    /**
     * ID of an element that contains description text inside this dialog.
     */
    "aria-describedby"?: string;
}
/**
 * Dialog component.
 *
 * @see https://blueprintjs.com/docs/#core/components/dialog
 */
export declare const Dialog: React.FC<DialogProps> & {
    displayName?: string;
};
