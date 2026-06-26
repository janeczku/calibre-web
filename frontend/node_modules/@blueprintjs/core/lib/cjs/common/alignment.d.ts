/** Alignment along the horizontal axis. */
export declare const Alignment: {
    CENTER: "center";
    END: "end";
    /**
     * @deprecated use `Alignment.START` instead.
     */
    LEFT: "left";
    /**
     * @deprecated use `Alignment.END` instead.
     */
    RIGHT: "right";
    START: "start";
};
export type Alignment = (typeof Alignment)[keyof typeof Alignment];
export declare const TextAlignment: {
    CENTER: "center";
    END: "end";
    START: "start";
};
export type TextAlignment = (typeof TextAlignment)[keyof typeof TextAlignment];
