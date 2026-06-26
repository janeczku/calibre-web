import type { Panel } from "./panelTypes";
export interface PanelViewProps<T extends Panel<object>> {
    /**
     * Callback invoked when the user presses the back button or a panel invokes
     * the `closePanel()` injected prop method.
     */
    onClose: (removedPanel: T) => void;
    /**
     * Callback invoked when a panel invokes the `openPanel(panel)` injected
     * prop method.
     */
    onOpen: (addedPanel: T) => void;
    /** The panel to be displayed. */
    panel: T;
    /** Ref to the root DOM element, used by PanelStack to provide `nodeRef` to CSSTransition. */
    panelNodeRef?: React.Ref<HTMLDivElement>;
    /** The previous panel in the stack, for rendering the "back" button. */
    previousPanel?: T;
    /** Whether to show the header with the "back" button. */
    showHeader: boolean;
}
interface PanelViewComponent {
    <T extends Panel<object>>(props: PanelViewProps<T>): React.JSX.Element | null;
    displayName: string;
}
export declare const PanelView: PanelViewComponent;
export {};
