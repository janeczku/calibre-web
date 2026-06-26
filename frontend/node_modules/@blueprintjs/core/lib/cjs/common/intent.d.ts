/**
 * The four basic intents.
 */
export declare const Intent: {
    NONE: "none";
    PRIMARY: "primary";
    SUCCESS: "success";
    WARNING: "warning";
    DANGER: "danger";
};
export type Intent = (typeof Intent)[keyof typeof Intent];
