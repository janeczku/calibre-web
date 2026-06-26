"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.PortalProvider = exports.PortalContext = void 0;
const jsx_runtime_1 = require("react/jsx-runtime");
/*
 * Copyright 2022 Palantir Technologies, Inc. All rights reserved.
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
 * A React context to set options for all portals in a given subtree.
 * Do not use this PortalContext directly, instead use PortalProvider to set the options.
 */
exports.PortalContext = (0, react_1.createContext)({});
/**
 * Portal context provider.
 *
 * @see https://blueprintjs.com/docs/#core/context/portal-provider
 */
const PortalProvider = ({ children, portalClassName, portalContainer, }) => {
    const contextOptions = (0, react_1.useMemo)(() => ({
        portalClassName,
        portalContainer,
    }), [portalClassName, portalContainer]);
    return (0, jsx_runtime_1.jsx)(exports.PortalContext.Provider, { value: contextOptions, children: children });
};
exports.PortalProvider = PortalProvider;
//# sourceMappingURL=portalProvider.js.map