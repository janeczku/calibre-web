import { Component } from "react";
import type { TreeEventHandler, TreeNodeInfo } from "./treeTypes";
export interface TreeNodeProps<T = {}> extends TreeNodeInfo<T> {
    children?: React.ReactNode;
    contentRef?: (node: TreeNodeInfo<T>, element: HTMLDivElement | null) => void;
    depth: number;
    key?: string | number;
    onClick?: TreeEventHandler<T>;
    onCollapse?: TreeEventHandler<T>;
    onContextMenu?: TreeEventHandler<T>;
    onDoubleClick?: TreeEventHandler<T>;
    onExpand?: TreeEventHandler<T>;
    onMouseEnter?: TreeEventHandler<T>;
    onMouseLeave?: TreeEventHandler<T>;
    path: number[];
}
/**
 * Tree node component.
 *
 * @see https://blueprintjs.com/docs/#core/components/tree.tree-node
 */
export declare class TreeNode<T = {}> extends Component<TreeNodeProps<T>> {
    static displayName: string;
    /** @deprecated no longer necessary now that the TypeScript parser supports type arguments on JSX element tags */
    static ofType<U>(): new (props: TreeNodeProps<U>) => TreeNode<U>;
    render(): import("react/jsx-runtime").JSX.Element;
    private maybeRenderCaret;
    private maybeRenderSecondaryLabel;
    private handleCaretClick;
    private handleClick;
    private handleContentRef;
    private handleContextMenu;
    private handleDoubleClick;
    private handleMouseEnter;
    private handleMouseLeave;
}
