"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.TooltipProvider = exports.TooltipContext = void 0;
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
const noOpDispatch = () => null;
exports.TooltipContext = (0, react_1.createContext)([
    {},
    noOpDispatch,
]);
const tooltipContextReducer = (state, action) => {
    switch (action.type) {
        case "FORCE_DISABLED_STATE":
            return { forceDisabled: true };
        case "RESET_DISABLED_STATE":
            return {};
        default:
            return state;
    }
};
const TooltipProvider = ({ children, forceDisable }) => {
    const [state, dispatch] = (0, react_1.useReducer)(tooltipContextReducer, {});
    const contextValue = (0, react_1.useMemo)(() => [state, dispatch], [state, dispatch]);
    (0, react_1.useEffect)(() => {
        if (forceDisable) {
            dispatch({ type: "FORCE_DISABLED_STATE" });
        }
        else {
            dispatch({ type: "RESET_DISABLED_STATE" });
        }
    }, [forceDisable]);
    return ((0, jsx_runtime_1.jsx)(exports.TooltipContext.Provider, { value: contextValue, children: typeof children === "function" ? children(state) : children }));
};
exports.TooltipProvider = TooltipProvider;
//# sourceMappingURL=tooltipContext.js.map