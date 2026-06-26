/** Boundary of a one-dimensional interval. */
export declare const Boundary: {
    START: "start";
    END: "end";
};
export type Boundary = (typeof Boundary)[keyof typeof Boundary];
