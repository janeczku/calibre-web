"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.Tree = void 0;
const tslib_1 = require("tslib");
const react_1 = require("react");
const jsx_runtime_1 = require("react/jsx-runtime");
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
const classnames_1 = tslib_1.__importDefault(require("classnames"));
const react_2 = require("react");
const common_1 = require("../../common");
const treeNode_1 = require("./treeNode");
/**
 * Tree component.
 *
 * @see https://blueprintjs.com/docs/#core/components/tree
 */
// eslint-disable-next-line @typescript-eslint/no-empty-object-type
class Tree extends react_2.Component {
    static displayName = `${common_1.DISPLAYNAME_PREFIX}.Tree`;
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
        return ((0, jsx_runtime_1.jsx)("div", { className: (0, classnames_1.default)(common_1.Classes.TREE, this.props.className, {
                [common_1.Classes.COMPACT]: this.props.compact,
            }), children: this.renderNodes(this.props.contents, [], common_1.Classes.TREE_ROOT) }));
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
            return ((0, react_1.createElement)(treeNode_1.TreeNode, { ...node, key: node.id, contentRef: this.handleContentRef, depth: elementPath.length - 1, onClick: this.handleNodeClick, onContextMenu: this.handleNodeContextMenu, onCollapse: this.handleNodeCollapse, onDoubleClick: this.handleNodeDoubleClick, onExpand: this.handleNodeExpand, onMouseEnter: this.handleNodeMouseEnter, onMouseLeave: this.handleNodeMouseLeave, path: elementPath }, this.renderNodes(node.childNodes, elementPath)));
        });
        return (0, jsx_runtime_1.jsx)("ul", { className: (0, classnames_1.default)(common_1.Classes.TREE_NODE_LIST, className), children: nodeItems });
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
exports.Tree = Tree;
//# sourceMappingURL=tree.js.map