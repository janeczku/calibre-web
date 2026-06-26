import { createElement as _createElement } from "react";
import { jsx as _jsx } from "react/jsx-runtime";
/*
 * Copyright 2015 Palantir Technologies, Inc. All rights reserved.
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *     http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */
import classNames from "classnames";
import { Component } from "react";
import { Classes, DISPLAYNAME_PREFIX } from "../../common";
import { TreeNode } from "./treeNode";
/**
 * Tree component.
 *
 * @see https://blueprintjs.com/docs/#core/components/tree
 */
// eslint-disable-next-line @typescript-eslint/no-empty-object-type
export class Tree extends Component {
    static displayName = `${DISPLAYNAME_PREFIX}.Tree`;
    static ofType() {
        return Tree;
    }
    static nodeFromPath(path, treeNodes) {
        if (path.length === 1) {
            return treeNodes[path[0]];
        }
        else {
            return Tree.nodeFromPath(path.slice(1), treeNodes[path[0]].childNodes);
        }
    }
    nodeRefs = {};
    render() {
        return (_jsx("div", { className: classNames(Classes.TREE, this.props.className, {
                [Classes.COMPACT]: this.props.compact,
            }), children: this.renderNodes(this.props.contents, [], Classes.TREE_ROOT) }));
    }
    /**
     * Returns the underlying HTML element of the `Tree` node with an id of `nodeId`.
     * This element does not contain the children of the node, only its label and controls.
     * If the node is not currently mounted, `undefined` is returned.
     */
    getNodeContentElement(nodeId) {
        return this.nodeRefs[nodeId];
    }
    renderNodes(treeNodes, currentPath, className) {
        if (treeNodes == null) {
            return null;
        }
        const nodeItems = treeNodes.map((node, i) => {
            const elementPath = currentPath.concat(i);
            return (_createElement(TreeNode, { ...node, key: node.id, contentRef: this.handleContentRef, depth: elementPath.length - 1, onClick: this.handleNodeClick, onContextMenu: this.handleNodeContextMenu, onCollapse: this.handleNodeCollapse, onDoubleClick: this.handleNodeDoubleClick, onExpand: this.handleNodeExpand, onMouseEnter: this.handleNodeMouseEnter, onMouseLeave: this.handleNodeMouseLeave, path: elementPath }, this.renderNodes(node.childNodes, elementPath)));
        });
        return _jsx("ul", { className: classNames(Classes.TREE_NODE_LIST, className), children: nodeItems });
    }
    handleContentRef = (node, element) => {
        if (element != null) {
            this.nodeRefs[node.id] = element;
        }
        else {
            // don't want our object to get bloated with old keys
            delete this.nodeRefs[node.id];
        }
    };
    handleNodeCollapse = (node, path, e) => {
        this.props.onNodeCollapse?.(node, path, e);
    };
    handleNodeClick = (node, path, e) => {
        this.props.onNodeClick?.(node, path, e);
    };
    handleNodeContextMenu = (node, path, e) => {
        this.props.onNodeContextMenu?.(node, path, e);
    };
    handleNodeDoubleClick = (node, path, e) => {
        this.props.onNodeDoubleClick?.(node, path, e);
    };
    handleNodeExpand = (node, path, e) => {
        this.props.onNodeExpand?.(node, path, e);
    };
    handleNodeMouseEnter = (node, path, e) => {
        this.props.onNodeMouseEnter?.(node, path, e);
    };
    handleNodeMouseLeave = (node, path, e) => {
        this.props.onNodeMouseLeave?.(node, path, e);
    };
}
//# sourceMappingURL=tree.js.map