"use strict";
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
Object.defineProperty(exports, "__esModule", { value: true });
exports.useTimeout = useTimeout;
const react_1 = require("react");
const useIsomorphicLayoutEffect_1 = require("./useIsomorphicLayoutEffect");
/**
 * React hook wrapper for setTimeout(), adapted from usehooks-ts.
 * The provided callback is invoked after the specified delay in milliseconds.
 * If the delay is null or the component is unmounted, any pending timeout is cleared.
 *
 * @see https://usehooks-ts.com/react-hook/use-timeout
 */
function useTimeout(callback, delay) {
    const savedCallback = (0, react_1.useRef)(callback);
    // remember the latest callback if it changes
    (0, useIsomorphicLayoutEffect_1.useIsomorphicLayoutEffect)(() => {
        savedCallback.current = callback;
    }, [callback]);
    // set up the timeout
    (0, react_1.useEffect)(() => {
        // Don't schedule if no delay is specified.
        // Note: 0 is a valid value for delay.
        if (!delay && delay !== 0) {
            return;
        }
        const id = setTimeout(() => savedCallback.current(), delay);
        return () => clearTimeout(id);
    }, [delay]);
}
//# sourceMappingURL=useTimeout.js.map