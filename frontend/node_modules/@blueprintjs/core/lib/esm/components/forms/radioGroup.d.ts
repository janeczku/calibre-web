import { type HTMLDivProps, type OptionProps, type Props } from "../../common";
export interface RadioGroupProps extends Props, HTMLDivProps {
    /**
     * Radio elements. This prop is mutually exclusive with `options`.
     * If passing custom children, ensure options have `role="radio"` or
     * `input` with `type="radio"`.
     */
    children?: React.ReactNode;
    /**
     * Whether the group and _all_ its radios are disabled.
     * Individual radios can be disabled using their `disabled` prop.
     */
    disabled?: boolean;
    /**
     * Whether the radio buttons are to be displayed inline horizontally.
     */
    inline?: boolean;
    /** Optional label text to display above the radio buttons. */
    label?: React.ReactNode;
    /**
     * Name of the group, used to link radio buttons together in HTML.
     * If omitted, a unique name will be generated internally.
     */
    name?: string;
    /**
     * Callback invoked when the currently selected radio changes.
     * Use `event.currentTarget.value` to read the currently selected value.
     * This prop is required because this component only supports controlled usage.
     */
    onChange: (event: React.ChangeEvent<HTMLInputElement>) => void;
    /**
     * Array of options to render in the group. This prop is mutually exclusive
     * with `children`: either provide an array of `OptionProps` objects or
     * provide `<Radio>` children elements.
     */
    options?: readonly OptionProps[];
    /** Value of the selected radio. The child with this value will be `:checked`. */
    selectedValue?: string | number;
}
/**
 * Radio group component.
 *
 * @see https://blueprintjs.com/docs/#core/components/radio.radiogroup
 */
export declare const RadioGroup: React.FC<RadioGroupProps>;
