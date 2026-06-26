import { type HTMLInputProps } from "../../common/props";
import { type CardProps } from "../card/card";
import type { CheckedControlProps, ControlProps } from "../forms/controlProps";
export type ControlKind = "switch" | "checkbox" | "radio";
/**
 * Subset of {@link CardProps} which can be used to adjust its behavior.
 */
type SupportedCardProps = Omit<CardProps, "interactive" | "onChange">;
/**
 * Subset of {@link ControlProps} which can be used to adjust its behavior.
 */
type SupportedControlProps = Pick<ControlProps, keyof CheckedControlProps | "alignIndicator" | "disabled" | "inputRef" | "label" | "value">;
/**
 * Shared props interface for all control card components, including `CheckboxCard`, `RadioCard`, and `SwitchCard`.
 * The label content may be specified as either `label` or `children`, but not both.
 */
export interface ControlCardProps extends SupportedCardProps, SupportedControlProps {
    /**
     * Which kind of form control to render inside the card.
     */
    controlKind: ControlKind;
    /**
     * HTML input attributes to forward to the control `<input>` element.
     */
    inputProps?: Omit<HTMLInputProps, "size">;
    /**
     * Whether the component should use "selected" Card styling when checked.
     *
     * @default true
     */
    showAsSelectedWhenChecked?: boolean;
}
export {};
