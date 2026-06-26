import { type Props } from "../../common/props";
export interface TextProps extends Props, React.RefAttributes<HTMLElement>, Omit<React.HTMLAttributes<HTMLElement>, "title"> {
    children?: React.ReactNode;
    /**
     * Indicates that this component should be truncated with an ellipsis if it overflows its container.
     * The `title` attribute will also be added when content overflows to show the full text of the children on hover.
     *
     * @default false
     */
    ellipsize?: boolean;
    /**
     * HTML tag name to use for rendered element.
     *
     * @default "div"
     */
    tagName?: keyof React.JSX.IntrinsicElements;
    /**
     * HTML title of the element
     */
    title?: string;
}
/**
 * Text component.
 *
 * @see https://blueprintjs.com/docs/#core/components/text
 */
export declare const Text: React.FC<TextProps>;
