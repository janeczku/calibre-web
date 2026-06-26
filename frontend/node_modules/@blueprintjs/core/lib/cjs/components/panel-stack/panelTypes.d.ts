/**
 * An object describing a panel in a `PanelStack`.
 */
export interface Panel<P> {
    /**
     * The renderer for this panel.
     */
    renderPanel: React.FC<PanelProps<P>>;
    /**
     * HTML title to be passed to the <Text> component
     */
    htmlTitle?: string;
    /**
     * The props passed to the component type when it is rendered. The methods
     * in `PanelActions` will be injected by `PanelStack`.
     */
    props?: P;
    /**
     * The title to be displayed above this panel. It is also used as the text
     * of the back button for any panel opened by this panel.
     */
    title?: React.ReactNode;
}
export interface PanelActions {
    /**
     * Call this method to programatically close this panel. If this is the only
     * panel on the stack then this method will do nothing.
     *
     * Remember that the panel header always contains a "back" button that
     * closes this panel on click (unless there is only one panel on the stack).
     */
    closePanel(): void;
    /**
     * Call this method to open a new panel on the top of the stack.
     */
    openPanel<P>(panel: Panel<P>): void;
}
/**
 * Use this interface in your panel component's props type to access these
 * panel action callbacks which are injected by `PanelStack`.
 *
 * See the code example in the docs website.
 *
 * @see https://blueprintjs.com/docs/#core/components/panel-stack
 */
export type PanelProps<P> = P & PanelActions;
