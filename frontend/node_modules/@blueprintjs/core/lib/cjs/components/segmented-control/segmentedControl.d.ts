import { Intent } from "../../common";
import { type ControlledValueProps, type OptionProps, type Props } from "../../common/props";
import type { Size } from "../../common/size";
import type { ButtonProps } from "../button/buttonProps";
export type SegmentedControlIntent = typeof Intent.NONE | typeof Intent.PRIMARY;
interface SegmentedControlOptionProps extends OptionProps<string> {
    icon?: ButtonProps["icon"];
}
/**
 * SegmentedControl component props.
 */
export interface SegmentedControlProps extends Props, ControlledValueProps<string>, React.RefAttributes<HTMLDivElement> {
    /**
     * Whether this control should be disabled.
     */
    disabled?: boolean;
    /**
     * Whether the control should take up the full width of its container.
     *
     * @default false
     */
    fill?: boolean;
    /**
     * Whether the control should appear as an inline element.
     */
    inline?: boolean;
    /**
     * Whether this control should use large buttons.
     *
     * @deprecated use `size="large"` instead.
     * @default false
     */
    large?: boolean;
    /**
     * Visual intent to apply to the selected value.
     */
    intent?: SegmentedControlIntent;
    /**
     * List of available options.
     */
    options: SegmentedControlOptionProps[];
    /**
     * Aria role for the overall component (container).
     * Child buttons get appropriate roles:
     * - "radiogroup" -> "radio"
     * - "group" -> "button"
     * - "toolbar" -> "button"
     * - "menu" -> "menuitemradio"
     *
     * @see https://www.w3.org/WAI/ARIA/apg/patterns/toolbar/examples/toolbar
     *
     * @default 'radiogroup'
     */
    role?: Extract<React.AriaRole, "radiogroup" | "group" | "toolbar" | "menu">;
    /**
     * The size of the control.
     *
     * @default "medium"
     */
    size?: Size;
    /**
     * Whether this control should use small buttons.
     *
     * @deprecated use `size="small"` instead.
     * @default false
     */
    small?: boolean;
}
/**
 * Segmented control component.
 *
 * @see https://blueprintjs.com/docs/#core/components/segmented-control
 */
export declare const SegmentedControl: React.FC<SegmentedControlProps>;
export {};
