import { Intent, type Props } from "../../common";
export interface LinkProps extends Props, React.RefAttributes<HTMLAnchorElement>, React.AnchorHTMLAttributes<HTMLAnchorElement> {
    /**
     * Child nodes to render inside the link.
     */
    children?: React.ReactNode;
    /**
     * Underline behavior for the link.
     *
     * - "always": Always shows underline (default)
     * - "hover": Shows underline only on hover
     * - "none": Never shows underline
     *
     * @default "always"
     */
    underline?: "always" | "hover" | "none";
    /**
     * Color of the link text.
     *
     * - Intent colors: "primary", "success", "warning", "danger"
     * - "inherit": Inherits color from surrounding text
     *
     * @default Intent.PRIMARY
     */
    color?: Intent | "inherit";
}
/**
 * Link component.
 *
 * @see https://blueprintjs.com/docs/#core/components/link
 */
export declare const Link: React.FC<LinkProps>;
