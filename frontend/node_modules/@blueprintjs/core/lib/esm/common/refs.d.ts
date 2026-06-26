export declare function isRefObject<T>(value: React.Ref<T> | undefined): value is React.RefObject<T>;
export declare function isRefCallback<T>(value: React.Ref<T> | undefined): value is React.RefCallback<T>;
/**
 * Assign the given ref to a target, either a React ref object or a callback which takes the ref as its first argument.
 */
export declare function setRef<T>(refTarget: React.Ref<T> | undefined, ref: T | null): void;
/**
 * Utility for merging refs into one singular callback ref.
 * If using in a functional component, would recomend using `useMemo` to preserve function identity.
 */
export declare function mergeRefs<T>(...refs: Array<React.Ref<T> | undefined>): React.RefCallback<T>;
export declare function getRef<T>(ref: T | React.RefObject<T> | null): T | null;
/**
 * Creates a ref handler which assigns the ref returned by React for a mounted component to a field on the target object.
 * The target object is usually a component class.
 *
 * If provided, it will also update the given `refProp` with the value of the ref.
 */
export declare function refHandler<T extends HTMLElement, K extends string>(refTargetParent: {
    [k in K]: T | null;
}, refTargetKey: K, refProp?: React.Ref<T> | undefined): React.RefCallback<T>;
