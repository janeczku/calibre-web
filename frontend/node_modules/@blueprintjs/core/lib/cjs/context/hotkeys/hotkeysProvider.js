"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.HotkeysProvider = exports.HotkeysContext = void 0;
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
const utils_1 = require("../../common/utils");
const hotkeysDialog_1 = require("../../components/hotkeys/hotkeysDialog");
const initialHotkeysState = { hasProvider: false, hotkeys: [], isDialogOpen: false };
const noOpDispatch = () => null;
/**
 * A React context used to register and deregister hotkeys as components are mounted and unmounted in an application.
 * Users should take care to make sure that only _one_ of these is instantiated and used within an application, especially
 * if using global hotkeys.
 *
 * You will likely not be using this HotkeysContext directly, except in cases where you need to get a direct handle on an
 * existing context instance for advanced use cases involving nested HotkeysProviders.
 *
 * For more information, see the [HotkeysProvider documentation](https://blueprintjs.com/docs/#core/context/hotkeys-provider).
 */
exports.HotkeysContext = (0, react_1.createContext)([initialHotkeysState, noOpDispatch]);
const hotkeysReducer = (state, action) => {
    switch (action.type) {
        case "ADD_HOTKEYS":
            // only pick up unique hotkeys which haven't been registered already
            const newUniqueHotkeys = [];
            for (const a of action.payload) {
                let isUnique = true;
                for (const b of state.hotkeys) {
                    isUnique &&= !(0, utils_1.shallowCompareKeys)(a, b, { exclude: ["onKeyDown", "onKeyUp"] });
                }
                if (isUnique) {
                    newUniqueHotkeys.push(a);
                }
            }
            return {
                ...state,
                hotkeys: [...state.hotkeys, ...newUniqueHotkeys],
            };
        case "REMOVE_HOTKEYS":
            return {
                ...state,
                hotkeys: state.hotkeys.filter(key => action.payload.indexOf(key) === -1),
            };
        case "OPEN_DIALOG":
            return { ...state, isDialogOpen: true };
        case "CLOSE_DIALOG":
            return { ...state, isDialogOpen: false };
        default:
            return state;
    }
};
/**
 * Hotkeys context provider, necessary for the `useHotkeys` hook.
 *
 * @see https://blueprintjs.com/docs/#core/context/hotkeys-provider
 */
const HotkeysProvider = ({ children, dialogProps, renderDialog, value, }) => {
    const hasExistingContext = value != null;
    const fallbackReducer = (0, react_1.useReducer)(hotkeysReducer, { ...initialHotkeysState, hasProvider: true });
    const [state, dispatch] = value ?? fallbackReducer;
    // The `useState` array isn't stable between renders -- so memo it outselves
    const contextValue = (0, react_1.useMemo)(() => [state, dispatch], [state, dispatch]);
    const handleDialogClose = (0, react_1.useCallback)(() => dispatch({ type: "CLOSE_DIALOG" }), [dispatch]);
    const dialog = renderDialog?.(state, { handleDialogClose }) ?? ((0, jsx_runtime_1.jsx)(hotkeysDialog_1.HotkeysDialog, { ...dialogProps, isOpen: state.isDialogOpen, hotkeys: state.hotkeys, onClose: handleDialogClose }));
    // if we are working with an existing context, we don't need to generate our own dialog
    return ((0, jsx_runtime_1.jsxs)(exports.HotkeysContext.Provider, { value: contextValue, children: [children, hasExistingContext ? undefined : dialog] }));
};
exports.HotkeysProvider = HotkeysProvider;
//# sourceMappingURL=hotkeysProvider.js.map