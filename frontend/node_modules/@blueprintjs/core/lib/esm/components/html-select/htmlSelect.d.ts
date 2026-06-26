import { type IconName, type SVGIconProps } from "@blueprintjs/icons";
import { type OptionProps } from "../../common/props";
import type { Extends } from "../../common/utils";
export type HTMLSelectIconName = Extends<IconName, "double-caret-vertical" | "caret-down">;
export interface HTMLSelectProps extends React.RefAttributes<HTMLSelectElement>, React.SelectHTMLAttributes<HTMLSelectElement> {
    children?: React.ReactNode;
    /** Whether this element is non-interactive. */
    disabled?: boolean;
    /** Whether this element should fill its container. */
    fill?: boolean;
    /**
     * Name of one of the supported icons for this component to display on the right side of the element.
     *
     * @default "double-caret-vertical"
     */
    iconName?: HTMLSelectIconName;
    /**
     * Props to spread to the icon element displayed on the right side of the element.
     */
    iconProps?: Partial<SVGIconProps>;
    /** Whether to use large styles. */
    large?: boolean;
    /** Whether to use minimal styles. */
    minimal?: boolean;
    /** Multiple select is not supported. */
    multiple?: never;
    /** Change event handler. Use `event.currentTarget.value` to access the new value. */
    onChange?: React.ChangeEventHandler<HTMLSelectElement>;
    /**
     * Shorthand for supplying options: an array of basic types or
     * `{ label?, value }` objects. If no `label` is supplied, `value`
     * will be used as the label.
     */
    options?: ReadonlyArray<string | number | OptionProps>;
    /** Controlled value of this component. */
    value?: string | number;
    /** Placeholder text to display when no option is selected. */
    placeholder?: string;
}
/**
 * HTML select component
 *
 * @see https://blueprintjs.com/docs/#core/components/html-select
 */
export declare const HTMLSelect: React.FC<HTMLSelectProps>;
