"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.OverlaysProvider = exports.OverlaysContext = void 0;
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
const react_1 = require("react");
/**
 * A React context used to interact with the overlay stack in an application.
 * Users should take care to make sure that only _one_ of these is instantiated and used within an
 * application.
 *
 * You will likely not be using this OverlaysContext directly, it's mostly used internally by the
 * Overlay2 component.
 *
 * For more information, see the [OverlaysProvider documentation](https://blueprintjs.com/docs/#core/context/overlays-provider).
 */
exports.OverlaysContext = (0, react_1.createContext)({
    hasProvider: false,
    stack: { current: [] },
});
/**
 * Overlays context provider, necessary for the `useOverlayStack` hook.
 *
 * @see https://blueprintjs.com/docs/#core/context/overlays-provider
 */
const OverlaysProvider = ({ children }) => {
    const stack = (0, react_1.useRef)([]);
    const contextValue = (0, react_1.useMemo)(() => ({ hasProvider: true, stack }), [stack]);
    return (0, jsx_runtime_1.jsx)(exports.OverlaysContext.Provider, { value: contextValue, children: children });
};
exports.OverlaysProvider = OverlaysProvider;
//# sourceMappingURL=overlaysProvider.js.map