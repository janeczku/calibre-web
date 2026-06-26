"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.TreeNode = void 0;
const tslib_1 = require("tslib");
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
const react_1 = require("react");
const icons_1 = require("@blueprintjs/icons");
const common_1 = require("../../common");
const collapse_1 = require("../collapse/collapse");
const icon_1 = require("../icon/icon");
/**
 * Tree node component.
 *
 * @see https://blueprintjs.com/docs/#core/components/tree.tree-node
 */
// eslint-disable-next-line @typescript-eslint/no-empty-object-type
class TreeNode extends react_1.Component {
    static displayName = `${common_1.DISPLAYNAME_PREFIX}.TreeNode`;
    /** @deprecated no longer necessary now that the TypeScript parser supports type arguments on JSX element tags */
    static ofType() {
        return TreeNode;
    }
    render() {
        const { children, className, disabled, icon, isExpanded, isSelected, label } = this.props;
        const classes = (0, classnames_1.default)(common_1.Classes.TREE_NODE, {
            [common_1.Classes.DISABLED]: disabled,
            [common_1.Classes.TREE_NODE_SELECTED]: isSelected,
            [common_1.Classes.TREE_NODE_EXPANDED]: isExpanded,
        }, className);
        const contentClasses = (0, classnames_1.default)(common_1.Classes.TREE_NODE_CONTENT, `${common_1.Classes.TREE_NODE_CONTENT}-${this.props.depth}`);
        const eventHandlers = disabled === true
            ? {}
            : {
                onClick: this.handleClick,
                onContextMenu: this.handleContextMenu,
                onDoubleClick: this.handleDoubleClick,
                onMouseEnter: this.handleMouseEnter,
                onMouseLeave: this.handleMouseLeave,
            };
        return ((0, jsx_runtime_1.jsxs)("li", { className: classes, children: [(0, jsx_runtime_1.jsxs)("div", { className: contentClasses, ref: this.handleContentRef, ...eventHandlers, children: [this.maybeRenderCaret(), (0, jsx_runtime_1.jsx)(icon_1.Icon, { className: common_1.Classes.TREE_NODE_ICON, icon: icon, "aria-hidden": true, tabIndex: -1 }), (0, jsx_runtime_1.jsx)("span", { className: common_1.Classes.TREE_NODE_LABEL, children: label }), this.maybeRenderSecondaryLabel()] }), (0, jsx_runtime_1.jsx)(collapse_1.Collapse, { isOpen: isExpanded, children: children })] }));
    }
    maybeRenderCaret() {
        const { children, isExpanded, disabled, hasCaret = react_1.Children.count(children) > 0 } = this.props;
        if (hasCaret) {
            const caretClasses = (0, classnames_1.default)(common_1.Classes.TREE_NODE_CARET, isExpanded ? common_1.Classes.TREE_NODE_CARET_OPEN : common_1.Classes.TREE_NODE_CARET_CLOSED);
            return ((0, jsx_runtime_1.jsx)(icons_1.ChevronRight, { title: isExpanded ? "Collapse group" : "Expand group", className: caretClasses, onClick: disabled === true ? undefined : this.handleCaretClick }));
        }
        return (0, jsx_runtime_1.jsx)("span", { className: common_1.Classes.TREE_NODE_CARET_NONE });
    }
    maybeRenderSecondaryLabel() {
        if (this.props.secondaryLabel != null) {
            return (0, jsx_runtime_1.jsx)("span", { className: common_1.Classes.TREE_NODE_SECONDARY_LABEL, children: this.props.secondaryLabel });
        }
        else {
            return undefined;
        }
    }
    handleCaretClick = (e) => {
        e.stopPropagation();
        const { isExpanded, onCollapse, onExpand } = this.props;
        (isExpanded ? onCollapse : onExpand)?.(this.props, this.props.path, e);
    };
    handleClick = (e) => {
        this.props.onClick?.(this.props, this.props.path, e);
    };
    handleContentRef = (element) => {
        this.props.contentRef?.(this.props, element);
    };
    handleContextMenu = (e) => {
        this.props.onContextMenu?.(this.props, this.props.path, e);
    };
    handleDoubleClick = (e) => {
        this.props.onDoubleClick?.(this.props, this.props.path, e);
    };
    handleMouseEnter = (e) => {
        this.props.onMouseEnter?.(this.props, this.props.path, e);
    };
    handleMouseLeave = (e) => {
        this.props.onMouseLeave?.(this.props, this.props.path, e);
    };
}
exports.TreeNode = TreeNode;
//# sourceMappingURL=treeNode.js.map