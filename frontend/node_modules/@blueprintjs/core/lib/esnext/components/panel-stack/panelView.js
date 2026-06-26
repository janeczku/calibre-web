import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
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
import { useCallback, useMemo } from "react";
import { Classes, DISPLAYNAME_PREFIX } from "../../common";
import { Button } from "../button/buttons";
import { Text } from "../text/text";
export const PanelView = ({ panel, onClose, onOpen, panelNodeRef, previousPanel, showHeader, }) => {
    const hasPreviousPanel = previousPanel !== undefined;
    const handleClose = useCallback(() => {
        // only remove this panel if it is not the only one.
        if (hasPreviousPanel) {
            onClose(panel);
        }
    }, [onClose, panel, hasPreviousPanel]);
    const maybeBackButton = previousPanel === undefined ? null : (_jsx(Button, { "aria-label": "Back", className: Classes.PANEL_STACK_HEADER_BACK, icon: "chevron-left", onClick: handleClose, size: "small", text: previousPanel.title, title: previousPanel.htmlTitle, variant: "minimal" }));
    // `panel.renderPanel` is simply a function that returns a React.JSX.Element. It may be an FC which
    // uses hooks. In order to avoid React errors due to inconsistent hook calls, we must encapsulate
    // those hooks with their own lifecycle through a very simple wrapper component.
    const PanelWrapper = useMemo(() => () => 
    // N.B. A type cast is required because of error TS2345, where technically `panel.props` could be
    // instantiated with a type unrelated to our generic constraint `T` here. We know
    // we're sending the right values here though, and it makes the consumer API for this
    // component type safe, so it's ok to do this...
    panel.renderPanel({
        closePanel: handleClose,
        openPanel: onOpen,
        ...panel.props,
    }), [panel, handleClose, onOpen]);
    return (_jsxs("div", { className: Classes.PANEL_STACK_VIEW, ref: panelNodeRef, children: [showHeader && (_jsxs("div", { className: Classes.PANEL_STACK_HEADER, children: [_jsx("span", { children: maybeBackButton }), _jsx(Text, { className: Classes.HEADING, ellipsize: true, title: panel.htmlTitle, children: panel.title }), _jsx("span", {})] })), _jsx(PanelWrapper, {})] }));
};
PanelView.displayName = `${DISPLAYNAME_PREFIX}.PanelView`;
//# sourceMappingURL=panelView.js.map