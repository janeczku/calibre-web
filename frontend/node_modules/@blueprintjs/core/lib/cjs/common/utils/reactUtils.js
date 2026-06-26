"use strict";
/*
 * Copyright 2020 Palantir Technologies, Inc. All rights reserved.
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
exports.isReactNodeEmpty = isReactNodeEmpty;
exports.isReactChildrenElementOrElements = isReactChildrenElementOrElements;
exports.ensureElement = ensureElement;
exports.isReactElement = isReactElement;
exports.isElementOfType = isElementOfType;
const react_1 = require("react");
const jsUtils_1 = require("./jsUtils");
/**
 * Returns true if `node` is null/undefined, false, empty string, or an array
 * composed of those. If `node` is an array, only one level of the array is
 * checked, for performance reasons.
 */
function isReactNodeEmpty(node, skipArray = false) {
    return (node == null ||
        node === "" ||
        node === false ||
        (!skipArray &&
            Array.isArray(node) &&
            // only recurse one level through arrays, for performance
            (node.length === 0 || node.every(n => isReactNodeEmpty(n, true)))));
}
/**
 * Returns true if children are a mappable children array
 *
 * @internal
 */
function isReactChildrenElementOrElements(children) {
    return !isReactNodeEmpty(children, true) && children !== true;
}
/**
 * Converts a React node to an element. Non-empty strings, numbers, and Fragments will be wrapped in given tag name;
 * empty strings and booleans will be discarded.
 *
 * @param child     the React node to convert
 * @param tagName   the HTML tag name to use when a wrapper element is needed
 * @param props     additional props to spread onto the element, if any. If the child is a React element and this argument
 *                  is defined, the child will be cloned and these props will be merged in.
 */
function ensureElement(child, tagName = "span", props = {}) {
    if (child == null || typeof child === "boolean" || (0, jsUtils_1.isEmptyString)(child)) {
        return undefined;
    }
    else if (typeof child === "string" ||
        typeof child === "number" ||
        isReactFragment(child) ||
        isReactNodeArray(child)) {
        // wrap the child element
        return (0, react_1.createElement)(tagName, props, child);
    }
    else if (isReactElement(child)) {
        if (Object.keys(props).length > 0) {
            // clone the element and merge props
            return (0, react_1.cloneElement)(child, props);
        }
        else {
            // nothing to do, it's a valid ReactElement
            return child;
        }
    }
    else {
        // child is inferred as {}
        return undefined;
    }
}
function isReactElement(child) {
    return (typeof child === "object" &&
        typeof child.type !== "undefined" &&
        typeof child.props !== "undefined");
}
function isReactFragment(child) {
    // bit hacky, but generally works
    return typeof child.type === "symbol";
}
function isReactNodeArray(child) {
    return Array.isArray(child);
}
/**
 * Returns true if the given JSX element matches the given component type.
 *
 * NOTE: This function only checks equality of `displayName` for performance and
 * to tolerate multiple minor versions of a component being included in one
 * application bundle.
 *
 * @param element JSX element in question
 * @param ComponentType desired component type of element
 */
// eslint-disable-next-line @typescript-eslint/no-empty-object-type
function isElementOfType(element, ComponentType) {
    return (element != null &&
        element.type != null &&
        element.type.displayName != null &&
        element.type.displayName === ComponentType.displayName);
}
//# sourceMappingURL=reactUtils.js.map