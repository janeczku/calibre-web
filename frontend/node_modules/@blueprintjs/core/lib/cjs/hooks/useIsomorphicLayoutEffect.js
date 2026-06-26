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
exports.useIsomorphicLayoutEffect = void 0;
const react_1 = require("react");
const domUtils_1 = require("../common/utils/domUtils");
/**
 * @returns the appropriate React layout effect hook for the current environment (server or client).
 */
exports.useIsomorphicLayoutEffect = (0, domUtils_1.hasDOMEnvironment)() ? react_1.useLayoutEffect : react_1.useEffect;
//# sourceMappingURL=useIsomorphicLayoutEffect.js.map