import { AbstractPureComponent, type Position } from "../../common";
import { type DialogProps } from "./dialog";
import { type DialogStepId } from "./dialogStep";
import { type DialogStepButtonProps } from "./dialogStepButton";
export type MultistepDialogNavPosition = typeof Position.TOP | typeof Position.LEFT | typeof Position.RIGHT;
export interface MultistepDialogProps extends DialogProps {
    /**
     * Props for the back button.
     */
    backButtonProps?: DialogStepButtonProps;
    /** Dialog steps. */
    children?: React.ReactNode;
    /**
     * Props for the close button that appears in the footer.
     */
    closeButtonProps?: DialogStepButtonProps;
    /**
     * Props for the button to display on the final step.
     */
    finalButtonProps?: DialogStepButtonProps;
    /**
     * Position of the step navigation within the dialog.
     *
     * @default "left"
     */
    navigationPosition?: MultistepDialogNavPosition;
    /**
     * Props for the next button.
     */
    nextButtonProps?: DialogStepButtonProps;
    /**
     * A callback that is invoked when the user selects a different step by clicking on back, next, or a step itself.
     */
    onChange?(newDialogStepId: DialogStepId, prevDialogStepId: DialogStepId | undefined, event: React.MouseEvent<HTMLElement>): void;
    /**
     * Whether to reset the dialog state to its initial state on close.
     * By default, closing the dialog will reset its state.
     *
     * @default true
     */
    resetOnClose?: boolean;
    /**
     * Whether the footer close button is shown. When this value is true, the button will appear
     * regardless of the value of `isCloseButtonShown`.
     *
     * @default false
     */
    showCloseButtonInFooter?: boolean;
    /**
     * A 0 indexed initial step to start off on, to start in the middle of the dialog, for example.
     * If the provided index exceeds the number of steps, it defaults to the last step.
     * If a negative index is provided, it defaults to the first step.
     */
    initialStepIndex?: number;
}
interface MultistepDialogState {
    lastViewedIndex: number;
    selectedIndex: number;
}
/**
 * Multi-step dialog component.
 *
 * @see https://blueprintjs.com/docs/#core/components/dialog.multistep-dialog
 */
export declare class MultistepDialog extends AbstractPureComponent<MultistepDialogProps, MultistepDialogState> {
    static displayName: string;
    static defaultProps: Partial<MultistepDialogProps>;
    state: MultistepDialogState;
    render(): import("react/jsx-runtime").JSX.Element;
    componentDidUpdate(prevProps: MultistepDialogProps): void;
    private getDialogStyle;
    private renderLeftPanel;
    private renderDialogStep;
    private maybeRenderRightPanel;
    private renderFooter;
    private renderButtons;
    private getDialogStepChangeHandler;
    /** Filters children to only `<DialogStep>`s */
    private getDialogStepChildren;
    private getInitialIndexFromProps;
}
export {};
