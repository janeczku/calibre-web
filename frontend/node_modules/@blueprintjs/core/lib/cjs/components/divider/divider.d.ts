import { type Props } from "../../common/props";
export interface DividerProps extends Props, React.HTMLAttributes<HTMLElement> {
    /**
     * If true, makes the Divider flush with adjacent content.
     *
     * @default false
     */
    compact?: boolean;
    /**
     * HTML tag to use for element.
     *
     * @default "div"
     */
    tagName?: keyof React.JSX.IntrinsicElements;
}
/**
 * Divider component.
 *
 * @see https://blueprintjs.com/docs/#core/components/divider
 */
export declare const Divider: React.FC<DividerProps>;
