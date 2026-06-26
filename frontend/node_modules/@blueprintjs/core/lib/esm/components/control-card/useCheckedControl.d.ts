import type { CheckedControlProps } from "../forms/controlProps";
/**
 * Keep track of a control's checked state in both controlled and uncontrolled modes
 */
export declare function useCheckedControl(props: CheckedControlProps): {
    checked: boolean;
    onChange: import("react").ChangeEventHandler<HTMLInputElement>;
};
