"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.PanelView = void 0;
const jsx_runtime_1 = require("react/jsx-runtime");
/*
 * Copyright 2021 Palantir Technologies, Inc. All rights reserved.
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
const react_1 = require("react");
const common_1 = require("../../common");
const buttons_1 = require("../button/buttons");
const text_1 = require("../text/text");
const PanelView = ({ panel, onClose, onOpen, panelNodeRef, previousPanel, showHeader, }) => {
    const hasPreviousPanel = previousPanel !== undefined;
    const handleClose = (0, react_1.useCallback)(() => {
        // only remove this panel if it is not the only one.
        if (hasPreviousPanel) {
            onClose(panel);
        }
    }, [onClose, panel, hasPreviousPanel]);
    const maybeBackButton = previousPanel === undefined ? null : ((0, jsx_runtime_1.jsx)(buttons_1.Button, { "aria-label": "Back", className: common_1.Classes.PANEL_STACK_HEADER_BACK, icon: "chevron-left", onClick: handleClose, size: "small", text: previousPanel.title, title: previousPanel.htmlTitle, variant: "minimal" }));
    // `panel.renderPanel` is simply a function that returns a React.JSX.Element. It may be an FC which
    // uses hooks. In order to avoid React errors due to inconsistent hook calls, we must encapsulate
    // those hooks with their own lifecycle through a very simple wrapper component.
    const PanelWrapper = (0, react_1.useMemo)(() => () => 
    // N.B. A type cast is required because of error TS2345, where technically `panel.props` could be
    // instantiated with a type unrelated to our generic constraint `T` here. We know
    // we're sending the right values here though, and it makes the consumer API for this
    // component type safe, so it's ok to do this...
    panel.renderPanel({
        closePanel: handleClose,
        openPanel: onOpen,
        ...panel.props,
    }), [panel, handleClose, onOpen]);
    return ((0, jsx_runtime_1.jsxs)("div", { className: common_1.Classes.PANEL_STACK_VIEW, ref: panelNodeRef, children: [showHeader && ((0, jsx_runtime_1.jsxs)("div", { className: common_1.Classes.PANEL_STACK_HEADER, children: [(0, jsx_runtime_1.jsx)("span", { children: maybeBackButton }), (0, jsx_runtime_1.jsx)(text_1.Text, { className: common_1.Classes.HEADING, ellipsize: true, title: panel.htmlTitle, children: panel.title }), (0, jsx_runtime_1.jsx)("span", {})] })), (0, jsx_runtime_1.jsx)(PanelWrapper, {})] }));
};
exports.PanelView = PanelView;
exports.PanelView.displayName = `${common_1.DISPLAYNAME_PREFIX}.PanelView`;
//# sourceMappingURL=panelView.js.map