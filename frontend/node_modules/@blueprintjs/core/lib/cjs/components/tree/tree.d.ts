import { Component } from "react";
import { type Props } from "../../common";
import type { TreeEventHandler, TreeNodeInfo } from "./treeTypes";
export interface TreeProps<T = {}> extends Props {
    /**
     * Whether to use a compact appearance which reduces the visual padding around node content.
     */
    compact?: boolean;
    /**
     * The data specifying the contents and appearance of the tree.
     */
    contents: ReadonlyArray<TreeNodeInfo<T>>;
    /**
     * Invoked when a node is clicked anywhere other than the caret for expanding/collapsing the node.
     */
    onNodeClick?: TreeEventHandler<T>;
    /**
     * Invoked when caret of an expanded node is clicked.
     */
    onNodeCollapse?: TreeEventHandler<T>;
    /**
     * Invoked when a node is right-clicked or the context menu button is pressed on a focused node.
     */
    onNodeContextMenu?: TreeEventHandler<T>;
    /**
     * Invoked when a node is double-clicked. Be careful when using this in combination with
     * an `onNodeClick` (single-click) handler, as the way this behaves can vary between browsers.
     * See http://stackoverflow.com/q/5497073/3124288
     */
    onNodeDoubleClick?: TreeEventHandler<T>;
    /**
     * Invoked when the caret of a collapsed node is clicked.
     */
    onNodeExpand?: TreeEventHandler<T>;
    /**
     * Invoked when the mouse is moved over a node.
     */
    onNodeMouseEnter?: TreeEventHandler<T>;
    /**
     * Invoked when the mouse is moved out of a node.
     */
    onNodeMouseLeave?: TreeEventHandler<T>;
}
/**
 * Tree component.
 *
 * @see https://blueprintjs.com/docs/#core/components/tree
 */
export declare class Tree<T = {}> extends Component<TreeProps<T>> {
    static displayName: string;
    static ofType<U>(): new (props: TreeProps<U>) => Tree<U>;
    static nodeFromPath<U>(path: readonly number[], treeNodes?: ReadonlyArray<TreeNodeInfo<U>>): TreeNodeInfo<U>;
    private nodeRefs;
    render(): import("react/jsx-runtime").JSX.Element;
    /**
     * Returns the underlying HTML element of the `Tree` node with an id of `nodeId`.
     * This element does not contain the children of the node, only its label and controls.
     * If the node is not currently mounted, `undefined` is returned.
     */
    getNodeContentElement(nodeId: string | number): HTMLElement | undefined;
    private renderNodes;
    private handleContentRef;
    private handleNodeCollapse;
    private handleNodeClick;
    private handleNodeContextMenu;
    private handleNodeDoubleClick;
    private handleNodeExpand;
    private handleNodeMouseEnter;
    private handleNodeMouseLeave;
}
