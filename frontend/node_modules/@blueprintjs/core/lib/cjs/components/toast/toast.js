"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.Toast2 = exports.Toast = void 0;
const tslib_1 = require("tslib");
const jsx_runtime_1 = require("react/jsx-runtime");
/*
 * Copyright 2024 Palantir Technologies, Inc. All rights reserved.
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
const props_1 = require("../../common/props");
const useTimeout_1 = require("../../hooks/useTimeout");
const buttonGroup_1 = require("../button/buttonGroup");
const buttons_1 = require("../button/buttons");
const icon_1 = require("../icon/icon");
/**
 * Toast component.
 *
 * @see https://blueprintjs.com/docs/#core/components/toast
 */
exports.Toast = (0, react_1.forwardRef)((props, ref) => {
    const { action, className, icon, intent, isCloseButtonShown = true, message, onDismiss, timeout = 5000 } = props;
    const [isTimeoutStarted, setIsTimeoutStarted] = (0, react_1.useState)(false);
    const startTimeout = (0, react_1.useCallback)(() => setIsTimeoutStarted(true), []);
    const clearTimeout = (0, react_1.useCallback)(() => setIsTimeoutStarted(false), []);
    // Per docs: "Providing a value less than or equal to 0 will disable the timeout (this is discouraged)."
    const isTimeoutEnabled = timeout != null && timeout > 0;
    // timeout is triggered & cancelled by updating `isTimeoutStarted` state
    (0, useTimeout_1.useTimeout)(() => {
        triggerDismiss(true);
    }, isTimeoutStarted && isTimeoutEnabled ? timeout : null);
    // start timeout on mount or change, cancel on unmount
    (0, react_1.useEffect)(() => {
        if (isTimeoutEnabled) {
            startTimeout();
        }
        else {
            clearTimeout();
        }
        return clearTimeout;
    }, [clearTimeout, startTimeout, isTimeoutEnabled, timeout]);
    const triggerDismiss = (0, react_1.useCallback)((didTimeoutExpire) => {
        clearTimeout();
        onDismiss?.(didTimeoutExpire);
    }, [clearTimeout, onDismiss]);
    const handleCloseClick = (0, react_1.useCallback)(() => triggerDismiss(false), [triggerDismiss]);
    const handleActionClick = (0, react_1.useCallback)((e) => {
        action?.onClick?.(e);
        triggerDismiss(false);
    }, [action, triggerDismiss]);
    return ((0, jsx_runtime_1.jsxs)("div", { className: (0, classnames_1.default)(common_1.Classes.TOAST, common_1.Classes.intentClass(intent), className), 
        // Pause timeouts if users are hovering over or click on the toast. The toast may have
        // actions the user wants to click. It'd be a poor experience to "pull the toast" out
        // from under them.
        onBlur: startTimeout, onFocus: clearTimeout, onMouseEnter: clearTimeout, onMouseLeave: startTimeout, ref: ref, 
        // eslint-disable-next-line jsx-a11y/no-noninteractive-tabindex
        tabIndex: 0, children: [(0, jsx_runtime_1.jsx)(icon_1.Icon, { icon: icon }), (0, jsx_runtime_1.jsx)("span", { className: common_1.Classes.TOAST_MESSAGE, role: "alert", children: message }), (0, jsx_runtime_1.jsxs)(buttonGroup_1.ButtonGroup, { variant: "minimal", children: [action && (0, jsx_runtime_1.jsx)(buttons_1.AnchorButton, { ...action, intent: undefined, onClick: handleActionClick }), isCloseButtonShown && (0, jsx_runtime_1.jsx)(buttons_1.Button, { "aria-label": "Close", icon: (0, jsx_runtime_1.jsx)(icons_1.Cross, {}), onClick: handleCloseClick })] })] }));
});
exports.Toast.displayName = `${props_1.DISPLAYNAME_PREFIX}.Toast`;
/** @deprecated Use `Toast` instead */
exports.Toast2 = exports.Toast;
//# sourceMappingURL=toast.js.map