"use strict";
/*
 * Copyright 2018 Palantir Technologies, Inc. All rights reserved.
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
exports.HandleInteractionKind = exports.HandleType = void 0;
exports.HandleType = {
    /** A full handle appears as a small square. */
    FULL: "full",
    /** A start handle appears as the left or top half of a square. */
    START: "start",
    /** An end handle appears as the right or bottom half of a square. */
    END: "end",
};
exports.HandleInteractionKind = {
    /** Locked handles prevent other handles from being dragged past then. */
    LOCK: "lock",
    /** Push handles move overlapping handles with them as they are dragged. */
    PUSH: "push",
    /**
     * Handles marked "none" are not interactive and do not appear in the UI.
     * They serve only to break the track into subsections that can be colored separately.
     */
    NONE: "none",
};
//# sourceMappingURL=handleProps.js.map