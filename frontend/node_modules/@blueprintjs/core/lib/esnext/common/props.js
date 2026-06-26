/*
 * Copyright 2015 Palantir Technologies, Inc. All rights reserved.
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
export const DISPLAYNAME_PREFIX = "Blueprint6";
/** A collection of curated prop keys used across our Components which are not valid HTMLElement props. */
const INVALID_PROPS = [
    "active",
    "alignText",
    "asyncControl", // InputGroupProps
    "containerRef",
    "current",
    "elementRef", // not used anymore in Blueprint v5.x, but kept for backcompat if consumers use this naming pattern
    "ellipsizeText", // ButtonProps
    "endIcon",
    "fill",
    "icon",
    "iconSize",
    "inputClassName",
    "inputRef",
    "intent",
    "inline",
    "large",
    "loading",
    "leftElement",
    "leftIcon",
    "minimal",
    "onRemove", // TagProps, TagInputProps
    "outlined", // ButtonProps
    "panel", // TabProps
    "panelClassName", // TabProps
    "popoverProps",
    "rightElement",
    "rightIcon",
    "round",
    "selectedValue",
    "size",
    "small",
    "tagName",
    "text",
    "textClassName", // ButtonProps
    "variant",
];
/**
 * Typically applied to HTMLElements to filter out disallowed props. When applied to a Component,
 * can filter props from being passed down to the children. Can also filter by a combined list of
 * supplied prop keys and the denylist (only appropriate for HTMLElements).
 *
 * @param props The original props object to filter down.
 * @param {string[]} invalidProps If supplied, overwrites the default denylist.
 * @param {boolean} shouldMerge If true, will merge supplied invalidProps and denylist together.
 */
export function removeNonHTMLProps(props, invalidProps = INVALID_PROPS, shouldMerge = false) {
    if (shouldMerge) {
        invalidProps = invalidProps.concat(INVALID_PROPS);
    }
    return invalidProps.reduce((prev, curr) => {
        // Props with hyphens (e.g. data-*) are always considered html props
        if (curr.indexOf("-") !== -1) {
            return prev;
        }
        if (prev.hasOwnProperty(curr)) {
            delete prev[curr];
        }
        return prev;
    }, { ...props });
}
//# sourceMappingURL=props.js.map