import { Elevation } from "../../common";
import { type HTMLDivProps, type Props } from "../../common/props";
export interface CardProps extends Props, HTMLDivProps, React.RefAttributes<HTMLDivElement> {
    /**
     * Controls the intensity of the drop shadow beneath the card: the higher
     * the elevation, the higher the drop shadow. At elevation `0`, no drop
     * shadow is applied.
     *
     * @default 0
     */
    elevation?: Elevation;
    /**
     * Whether the card should respond to user interactions. If set to `true`,
     * hovering over the card will increase the card's elevation
     * and change the mouse cursor to a pointer.
     *
     * Recommended when `onClick` is also defined.
     *
     * @default false
     */
    interactive?: boolean;
    /**
     * Whether this card should appear selected.
     *
     * @default undefined
     */
    selected?: boolean;
    /**
     * Whether this component should use compact styles with reduced visual padding.
     *
     * @default false
     */
    compact?: boolean;
    /**
     * Callback invoked when the card is clicked.
     * Recommended when `interactive` is `true`.
     */
    onClick?: (e: React.MouseEvent<HTMLDivElement>) => void;
}
/**
 * Card component.
 *
 * @see https://blueprintjs.com/docs/#core/components/card
 */
export declare const Card: React.FC<CardProps>;
