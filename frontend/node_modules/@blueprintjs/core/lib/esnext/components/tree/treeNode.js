import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
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
import { Children, Component } from "react";
import { ChevronRight } from "@blueprintjs/icons";
import { Classes, DISPLAYNAME_PREFIX } from "../../common";
import { Collapse } from "../collapse/collapse";
import { Icon } from "../icon/icon";
/**
 * Tree node component.
 *
 * @see https://blueprintjs.com/docs/#core/components/tree.tree-node
 */
// eslint-disable-next-line @typescript-eslint/no-empty-object-type
export class TreeNode extends Component {
    static displayName = `${DISPLAYNAME_PREFIX}.TreeNode`;
    /** @deprecated no longer necessary now that the TypeScript parser supports type arguments on JSX element tags */
    static ofType() {
        return TreeNode;
    }
    render() {
        const { children, className, disabled, icon, isExpanded, isSelected, label } = this.props;
        const classes = classNames(Classes.TREE_NODE, {
            [Classes.DISABLED]: disabled,
            [Classes.TREE_NODE_SELECTED]: isSelected,
            [Classes.TREE_NODE_EXPANDED]: isExpanded,
        }, className);
        const contentClasses = classNames(Classes.TREE_NODE_CONTENT, `${Classes.TREE_NODE_CONTENT}-${this.props.depth}`);
        const eventHandlers = disabled === true
            ? {}
            : {
                onClick: this.handleClick,
                onContextMenu: this.handleContextMenu,
                onDoubleClick: this.handleDoubleClick,
                onMouseEnter: this.handleMouseEnter,
                onMouseLeave: this.handleMouseLeave,
            };
        return (_jsxs("li", { className: classes, children: [_jsxs("div", { className: contentClasses, ref: this.handleContentRef, ...eventHandlers, children: [this.maybeRenderCaret(), _jsx(Icon, { className: Classes.TREE_NODE_ICON, icon: icon, "aria-hidden": true, tabIndex: -1 }), _jsx("span", { className: Classes.TREE_NODE_LABEL, children: label }), this.maybeRenderSecondaryLabel()] }), _jsx(Collapse, { isOpen: isExpanded, children: children })] }));
    }
    maybeRenderCaret() {
        const { children, isExpanded, disabled, hasCaret = Children.count(children) > 0 } = this.props;
        if (hasCaret) {
            const caretClasses = classNames(Classes.TREE_NODE_CARET, isExpanded ? Classes.TREE_NODE_CARET_OPEN : Classes.TREE_NODE_CARET_CLOSED);
            return (_jsx(ChevronRight, { title: isExpanded ? "Collapse group" : "Expand group", className: caretClasses, onClick: disabled === true ? undefined : this.handleCaretClick }));
        }
        return _jsx("span", { className: Classes.TREE_NODE_CARET_NONE });
    }
    maybeRenderSecondaryLabel() {
        if (this.props.secondaryLabel != null) {
            return _jsx("span", { className: Classes.TREE_NODE_SECONDARY_LABEL, children: this.props.secondaryLabel });
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
//# sourceMappingURL=treeNode.js.map