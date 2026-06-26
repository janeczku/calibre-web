/**
 * Returns true if `node` is null/undefined, false, empty string, or an array
 * composed of those. If `node` is an array, only one level of the array is
 * checked, for performance reasons.
 */
export declare function isReactNodeEmpty(node?: React.ReactNode, skipArray?: boolean): boolean;
/**
 * Converts a React node to an element. Non-empty strings, numbers, and Fragments will be wrapped in given tag name;
 * empty strings and booleans will be discarded.
 *
 * @param child     the React node to convert
 * @param tagName   the HTML tag name to use when a wrapper element is needed
 * @param props     additional props to spread onto the element, if any. If the child is a React element and this argument
 *                  is defined, the child will be cloned and these props will be merged in.
 */
export declare function ensureElement(child: React.ReactNode | undefined, tagName?: keyof React.JSX.IntrinsicElements, props?: React.HTMLProps<HTMLElement>): import("react").ReactElement<any, string | import("react").JSXElementConstructor<any>> | undefined;
export declare function isReactElement<T = any>(child: React.ReactNode): child is React.ReactElement<T>;
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
export declare function isElementOfType<P = {}>(element: any, ComponentType: React.ComponentType<P>): element is React.ReactElement<P>;
