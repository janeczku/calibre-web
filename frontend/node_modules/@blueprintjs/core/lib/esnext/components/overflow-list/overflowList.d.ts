import { Component } from "react";
import { Boundary, type Props } from "../../common";
export interface OverflowListProps<T> extends Props {
    /**
     * Whether to force the overflowRenderer to always be called, even if there are zero items
     * overflowing. This may be useful, for example, if your overflow renderer contains a Popover
     * which you do not want to close as the list is resized.
     *
     * @default false
     */
    alwaysRenderOverflow?: boolean;
    /**
     * Which direction the items should collapse from: start or end of the
     * children. This also determines whether `overflowRenderer` appears before
     * (`START`) or after (`END`) the visible items.
     *
     * @default Boundary.START
     */
    collapseFrom?: Boundary;
    /**
     * All items to display in the list. Items that do not fit in the container
     * will be rendered in the overflow instead.
     */
    items: readonly T[];
    /**
     * The minimum number of visible items that should never collapse into the
     * overflow menu, regardless of DOM dimensions.
     *
     * @default 0
     */
    minVisibleItems?: number;
    /**
     * If `true`, all parent DOM elements of the container will also be
     * observed. If changes to a parent's size is detected, the overflow will be
     * recalculated.
     *
     * Only enable this prop if the overflow should be recalculated when a
     * parent element resizes in a way that does not also cause the
     * `OverflowList` to resize.
     *
     * @default false
     */
    observeParents?: boolean;
    /**
     * Callback invoked when the overflowed items change. This is called once
     * after the DOM has settled, rather that on every intermediate change. It
     * is not invoked if resizing produces an unchanged overflow state.
     */
    onOverflow?: (overflowItems: T[]) => void;
    /**
     * Callback invoked to render the overflowed items. Unlike
     * `visibleItemRenderer`, this prop is invoked once with all items that do
     * not fit in the container.
     *
     * Typical use cases for this prop will put overflowed items in a dropdown
     * menu or display a "+X items" label.
     */
    overflowRenderer: (overflowItems: T[]) => React.ReactNode;
    /** CSS properties to apply to the root element. */
    style?: React.CSSProperties;
    /**
     * HTML tag name for the container element.
     *
     * @default "div"
     */
    tagName?: keyof React.JSX.IntrinsicElements;
    /**
     * Callback invoked to render each visible item.
     * Remember to set a `key` on the rendered element!
     */
    visibleItemRenderer: (item: T, index: number) => React.ReactNode;
    /**
     * If true, the overflow list will be wrapped with a `nav` element.
     *
     * @default false
     */
    navigable?: boolean;
    /**
     * ARIA label to apply to the `nav` element. Only used if `navigable` is true.
     *
     * @default ""
     */
    navigationAriaLabel?: string;
}
export interface OverflowListState<T> {
    /** Whether repartitioning is still active. An overflow can take several frames to settle. */
    repartitioning: boolean;
    /** Length of last overflow to dedupe `onOverflow` calls during smooth resizing. */
    lastOverflowCount: number;
    overflow: readonly T[];
    visible: readonly T[];
    /** Pointer for the binary search algorithm used to find the finished non-overflowing state */
    chopSize: number;
    lastChopSize: number | null;
}
/**
 * Overflow list component.
 *
 * @see https://blueprintjs.com/docs/#core/components/overflow-list
 */
export declare class OverflowList<T> extends Component<OverflowListProps<T>, OverflowListState<T>> {
    static displayName: string;
    static defaultProps: Partial<OverflowListProps<any>>;
    static ofType<U>(): new (props: OverflowListProps<U>) => OverflowList<U>;
    state: OverflowListState<T>;
    private spacer;
    componentDidMount(): void;
    shouldComponentUpdate(nextProps: OverflowListProps<T>, nextState: OverflowListState<T>): boolean;
    componentDidUpdate(prevProps: OverflowListProps<T>, prevState: OverflowListState<T>): void;
    render(): import("react/jsx-runtime").JSX.Element;
    private maybeRenderOverflow;
    private resize;
    private repartition;
    private defaultChopSize;
    private isFirstPartitionCycle;
}
