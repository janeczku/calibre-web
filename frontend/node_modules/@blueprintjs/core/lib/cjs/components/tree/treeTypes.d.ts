import type { MaybeElement } from "../../common/props";
import type { IconName } from "../icon/icon";
export interface TreeNodeInfo<T = {}> {
    /**
     * A space-delimited list of class names for this tree node element.
     */
    className?: string;
    /**
     * Child tree nodes of this node.
     */
    childNodes?: Array<TreeNodeInfo<T>>;
    /**
     * Whether this tree node is non-interactive. Enabling this prop will ignore
     * mouse event handlers (in particular click, down, enter, leave).
     */
    disabled?: boolean;
    /**
     * Whether the caret to expand/collapse a node should be shown.
     * If not specified, this will be true if the node has children and false otherwise.
     */
    hasCaret?: boolean;
    /**
     * The name of a Blueprint icon (or an icon element) to render next to the node's label.
     */
    icon?: IconName | MaybeElement;
    /**
     * A unique identifier for the node.
     */
    id: string | number;
    /**
     */
    isExpanded?: boolean;
    /**
     * Whether this node is selected.
     *
     * @default false
     */
    isSelected?: boolean;
    /**
     * The main label for the node.
     */
    label: string | React.JSX.Element;
    /**
     * A secondary label/component that is displayed at the right side of the node.
     */
    secondaryLabel?: string | MaybeElement;
    /**
     * An optional custom user object to associate with the node.
     * This property can then be used in the `onClick`, `onContextMenu` and `onDoubleClick`
     * event handlers for doing custom logic per node.
     */
    nodeData?: T;
}
export type TreeEventHandler<T = {}> = (node: TreeNodeInfo<T>, nodePath: number[], e: React.MouseEvent<HTMLElement>) => void;
