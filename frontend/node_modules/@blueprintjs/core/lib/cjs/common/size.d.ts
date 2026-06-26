/** The rendering size of a component. */
export declare const Size: {
    readonly SMALL: "small";
    readonly MEDIUM: "medium";
    readonly LARGE: "large";
};
export type Size = (typeof Size)[keyof typeof Size];
/** A subset of `Size` which excludes `"small"` */
export type NonSmallSize = Exclude<Size, "small">;
