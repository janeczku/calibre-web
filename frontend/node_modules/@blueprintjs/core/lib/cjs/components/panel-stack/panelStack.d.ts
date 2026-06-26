import { type Props } from "../../common";
import type { Panel } from "./panelTypes";
/** @deprecated Use `PanelStackProps` instead */
export type PanelStack2Props<T extends Panel<object>> = PanelStackProps<T>;
/**
 * @template T type union of all possible panels in this stack
 */
export interface PanelStackProps<T extends Panel<object>> extends Props {
    /**
     * The initial panel to show on mount. This panel cannot be removed from the
     * stack and will appear when the stack is empty.
     * This prop is only used in uncontrolled mode and is thus mutually
     * exclusive with the `stack` prop.
     */
    initialPanel?: T;
    /**
     * Callback invoked when the user presses the back button or a panel
     * closes itself with a `closePanel()` action.
     */
    onClose?: (removedPanel: T) => void;
    /**
     * Callback invoked when a panel opens a new panel with an `openPanel(panel)`
     * action.
     */
    onOpen?: (addedPanel: T) => void;
    /**
     * If false, PanelStack will render all panels in the stack to the DOM, allowing their
     * React component trees to maintain state as a user navigates through the stack.
     * Panels other than the currently active one will be invisible.
     *
     * @default true
     */
    renderActivePanelOnly?: boolean;
    /**
     * Whether to show the header with the "back" button in each panel.
     *
     * @default true
     */
    showPanelHeader?: boolean;
    /**
     * The full stack of panels in controlled mode. The last panel in the stack
     * will be displayed.
     */
    stack?: readonly T[];
}
interface PanelStackComponent {
    /**
     * @template T type union of all possible panels in this stack
     */
    <T extends Panel<object>>(props: PanelStackProps<T>): React.JSX.Element | null;
    displayName: string;
}
/**
 * Panel stack component.
 *
 * @see https://blueprintjs.com/docs/#core/components/panel-stack
 * @template T type union of all possible panels in this stack
 */
export declare const PanelStack: PanelStackComponent;
/** @deprecated Use `PanelStack` instead */
export declare const PanelStack2: PanelStackComponent;
export type PanelStack2 = PanelStackComponent;
export {};
