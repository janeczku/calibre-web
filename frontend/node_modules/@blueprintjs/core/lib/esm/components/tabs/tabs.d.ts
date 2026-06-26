import { AbstractPureComponent, type NonSmallSize, type Props } from "../../common";
import { Tab, type TabId } from "./tab";
/**
 * Component that may be inserted between any two children of `<Tabs>` to right-align all subsequent children.
 */
export declare const TabsExpander: React.FC;
export interface TabsProps extends Props {
    /**
     * Whether the selected tab indicator should animate its movement.
     *
     * @default true
     */
    animate?: boolean;
    /** Tab elements. */
    children?: React.ReactNode;
    /**
     * Initial selected tab `id`, for uncontrolled usage.
     * Note that this prop refers only to `<Tab>` children; other types of elements are ignored.
     *
     * @default first tab
     */
    defaultSelectedTabId?: TabId;
    /**
     * Unique identifier for this `Tabs` container. This will be combined with the `id` of each
     * `Tab` child to generate ARIA accessibility attributes. IDs are required and should be
     * unique on the page to support server-side rendering.
     */
    id: TabId;
    /**
     * If set to `true`, the tab titles will display with larger styling.
     * This will apply large styles only to the tabs at this level, not to nested tabs.
     *
     * @deprecated use `size="large"` instead
     * @default false
     */
    large?: boolean;
    /**
     * The size of the tab titles.
     *
     * @default "medium"
     */
    size?: NonSmallSize;
    /**
     * Whether inactive tab panels should be removed from the DOM and unmounted in React.
     * This can be a performance enhancement when rendering many complex panels, but requires
     * careful support for unmounting and remounting.
     *
     * @default false
     */
    renderActiveTabPanelOnly?: boolean;
    /**
     * Selected tab `id`, for controlled usage.
     * Providing this prop will put the component in controlled mode.
     * Unknown ids will result in empty selection (no errors).
     */
    selectedTabId?: TabId;
    /**
     * Whether to show tabs stacked vertically on the left side.
     *
     * @default false
     */
    vertical?: boolean;
    /**
     * Whether to make the tabs list fill the height of its parent.
     *
     * This has no effect when `vertical={true}`.
     * This is not recommended when tab panels are defined within this component subtree, as the height computation will
     * include the panel height, which is usually not intended. Instead, it works well if the panels are rendered
     * elsewhere in the React tree.
     *
     * @default false
     */
    fill?: boolean;
    /**
     * A callback function that is invoked when a tab in the tab list is clicked.
     */
    onChange?(newTabId: TabId, prevTabId: TabId | undefined, event: React.MouseEvent<HTMLElement>): void;
}
export interface TabsState {
    indicatorWrapperStyle?: React.CSSProperties;
    selectedTabId?: TabId;
}
/**
 * Tabs component.
 *
 * @see https://blueprintjs.com/docs/#core/components/tabs
 */
export declare class Tabs extends AbstractPureComponent<TabsProps, TabsState> {
    /**
     * @deprecated Use the `Tab` component directly instead
     *
     * @see https://blueprintjs.com/docs/#core/components/tabs.tab
     */
    static Tab: typeof Tab;
    static defaultProps: Partial<TabsProps>;
    static displayName: string;
    static getDerivedStateFromProps({ selectedTabId }: TabsProps): {
        selectedTabId: TabId;
    } | null;
    private tablistElement;
    private refHandlers;
    constructor(props: TabsProps);
    render(): import("react/jsx-runtime").JSX.Element;
    componentDidMount(): void;
    componentDidUpdate(prevProps: TabsProps, prevState: TabsState): void;
    private getInitialSelectedTabId;
    private getTabChildrenProps;
    /** Filters children to only `<Tab>`s */
    private getTabChildren;
    /** Queries root HTML element for all tabs with optional filter selector */
    private getTabElements;
    private handleKeyDown;
    private handleKeyPress;
    private handleTabClick;
    /**
     * Calculate the new height, width, and position of the tab indicator.
     * Store the CSS values so the transition animation can start.
     */
    private moveSelectionIndicator;
    private renderTabPanel;
    private renderTabTitle;
}
