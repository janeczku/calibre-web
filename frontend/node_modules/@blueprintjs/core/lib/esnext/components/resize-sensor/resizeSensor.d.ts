import { AbstractPureComponent } from "../../common";
export type ResizeEntry = ResizeObserverEntry;
/** `ResizeSensor` requires a single DOM element child and will error otherwise. */
export interface ResizeSensorProps {
    /**
     * Single child, must be an element and not a string or fragment.
     */
    children: React.JSX.Element;
    /**
     * Callback invoked when the wrapped element resizes.
     *
     * The `entries` array contains an entry for each observed element. In the
     * default case (no `observeParents`), the array will contain only one
     * element: the single child of the `ResizeSensor`.
     *
     * Note that this method is called _asynchronously_ after a resize is
     * detected and typically it will be called no more than once per frame.
     */
    onResize: (entries: ResizeObserverEntry[]) => void;
    /**
     * If `true`, all parent DOM elements of the container will also be
     * observed for size changes. The array of entries passed to `onResize`
     * will now contain an entry for each parent element up to the root of the
     * document.
     *
     * Only enable this prop if a parent element resizes in a way that does
     * not also cause the child element to resize.
     *
     * @default false
     */
    observeParents?: boolean;
    /**
     * If you attach a `ref` to the child yourself when rendering it, you must pass the
     * same value here (otherwise, ResizeSensor won't be able to attach its own).
     */
    targetRef?: React.RefObject<HTMLElement>;
}
/**
 * Resize sensor component.
 *
 * It requires a single DOM element child and will error otherwise.
 *
 * @see https://blueprintjs.com/docs/#core/components/resize-sensor
 **/
export declare class ResizeSensor extends AbstractPureComponent<ResizeSensorProps> {
    static displayName: string;
    private targetRef;
    private prevElement;
    private observer;
    render(): React.ReactNode;
    componentDidMount(): void;
    componentDidUpdate(prevProps: ResizeSensorProps): void;
    componentWillUnmount(): void;
    /**
     * Observe the DOM element, if defined and different from the currently
     * observed element. Pass `force` argument to skip element checks and always
     * re-observe.
     */
    private observeElement;
}
