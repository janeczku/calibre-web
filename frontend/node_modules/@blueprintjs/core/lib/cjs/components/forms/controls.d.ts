import type { ControlProps } from "./controlProps";
/**
 * Switch component props.
 */
export interface SwitchProps extends ControlProps {
    /**
     * Text to display inside the switch indicator when checked.
     * If `innerLabel` is provided and this prop is omitted, then `innerLabel`
     * will be used for both states.
     *
     * @default innerLabel
     */
    innerLabelChecked?: string;
    /**
     * Text to display inside the switch indicator when unchecked.
     */
    innerLabel?: string;
}
/**
 * Switch component.
 *
 * @see https://blueprintjs.com/docs/#core/components/switch
 */
export declare const Switch: React.FC<SwitchProps>;
/**
 * Radio component props.
 */
export type RadioProps = ControlProps;
/**
 * Radio component.
 *
 * @see https://blueprintjs.com/docs/#core/components/radio
 */
export declare const Radio: React.FC<RadioProps>;
/**
 * Checkbox component props.
 */
export interface CheckboxProps extends ControlProps {
    /** Whether this checkbox is initially indeterminate (uncontrolled mode). */
    defaultIndeterminate?: boolean;
    /**
     * Whether this checkbox is indeterminate, or "partially checked."
     * The checkbox will appear with a small dash instead of a tick to indicate that the value
     * is not exactly true or false.
     *
     * Note that this prop takes precendence over `checked`: if a checkbox is marked both
     * `checked` and `indeterminate` via props, it will appear as indeterminate in the DOM.
     */
    indeterminate?: boolean;
}
/**
 * Checkbox component.
 *
 * @see https://blueprintjs.com/docs/#core/components/checkbox
 */
export declare const Checkbox: React.FC<CheckboxProps>;
