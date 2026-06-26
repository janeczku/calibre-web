import { type IntentProps, type Props } from "../../common/props";
export declare enum SpinnerSize {
    SMALL = 20,
    STANDARD = 50,
    LARGE = 100
}
export interface SpinnerProps<T extends HTMLElement = HTMLElement> extends Props, IntentProps, React.HTMLAttributes<T> {
    /**
     * Width and height of the spinner in pixels. The size cannot be less than
     * 10px.
     *
     * Constants are available for common sizes:
     * - `SpinnerSize.SMALL = 20px`
     * - `SpinnerSize.STANDARD = 50px`
     * - `SpinnerSize.LARGE = 100px`
     *
     * @default SpinnerSize.STANDARD = 50
     */
    size?: number;
    /**
     * HTML tag for the two wrapper elements. If rendering a `<Spinner>` inside
     * an `<svg>`, change this to an SVG element like `"g"`.
     *
     * @default "div"
     */
    tagName?: keyof React.JSX.IntrinsicElements;
    /**
     * A value between 0 and 1 (inclusive) representing how far along the operation is.
     * Values below 0 or above 1 will be interpreted as 0 or 1 respectively.
     * Omitting this prop will result in an "indeterminate" spinner where the head spins indefinitely.
     */
    value?: number;
}
/**
 * Spinner component.
 *
 * @see https://blueprintjs.com/docs/#core/components/spinner
 */
export declare const Spinner: React.FC<SpinnerProps>;
