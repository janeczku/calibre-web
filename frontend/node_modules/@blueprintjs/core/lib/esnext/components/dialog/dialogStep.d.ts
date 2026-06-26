import { type HTMLDivProps, type Props } from "../../common/props";
import type { DialogStepButtonProps } from "./dialogStepButton";
export type DialogStepId = string | number;
export interface DialogStepProps extends Props, Omit<HTMLDivProps, "id" | "title" | "onClick"> {
    /**
     * Unique identifier used to identify which step is selected.
     */
    id: DialogStepId;
    /**
     * Panel content, rendered by the parent `MultistepDialog` when this step is active.
     */
    panel: React.JSX.Element;
    /**
     * Space-delimited string of class names applied to multistep dialog panel container.
     */
    panelClassName?: string;
    /**
     * Content of step title element, rendered in a list left of the active panel.
     */
    title?: React.ReactNode;
    /**
     * Props for the back button.
     */
    backButtonProps?: DialogStepButtonProps;
    /**
     * Props for the next button.
     */
    nextButtonProps?: DialogStepButtonProps;
}
/**
 * Dialog step component.
 *
 * @see https://blueprintjs.com/docs/#core/components/dialog.dialogstep
 */
export declare const DialogStep: React.FC<DialogStepProps>;
