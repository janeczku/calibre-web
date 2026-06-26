"use strict";
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
Object.defineProperty(exports, "__esModule", { value: true });
exports.HotkeysTarget2 = exports.HotkeysTarget = void 0;
const tslib_1 = require("tslib");
const react_1 = require("react");
const Errors = tslib_1.__importStar(require("../../common/errors"));
const utils_1 = require("../../common/utils");
const hooks_1 = require("../../hooks");
/**
 * Utility component which allows consumers to use the new `useHotkeys` hook inside
 * React component classes. The implementation simply passes through to the hook.
 */
const HotkeysTarget = ({ children, hotkeys, options }) => {
    const { handleKeyDown, handleKeyUp } = (0, hooks_1.useHotkeys)(hotkeys, options);
    // run props validation
    (0, react_1.useEffect)(() => {
        if (!(0, utils_1.isNodeEnv)("production")) {
            if (typeof children !== "function" && hotkeys.some(h => !h.global)) {
                console.error(Errors.HOTKEYS_TARGET_CHILDREN_LOCAL_HOTKEYS);
            }
        }
    }, [hotkeys, children]);
    if ((0, utils_1.isFunction)(children)) {
        return children({ handleKeyDown, handleKeyUp });
    }
    else {
        return children;
    }
};
exports.HotkeysTarget = HotkeysTarget;
/** @deprecated Use `HotkeysTarget` instead */
exports.HotkeysTarget2 = exports.HotkeysTarget;
//# sourceMappingURL=hotkeysTarget.js.map