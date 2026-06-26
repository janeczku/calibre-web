export interface TooltipContextState {
    forceDisabled?: boolean;
}
type TooltipAction = {
    type: "FORCE_DISABLED_STATE";
} | {
    type: "RESET_DISABLED_STATE";
};
export declare const TooltipContext: import("react").Context<readonly [TooltipContextState, import("react").Dispatch<TooltipAction>]>;
interface TooltipProviderProps {
    children: React.ReactNode | ((ctxState: TooltipContextState) => React.ReactNode);
    forceDisable?: boolean;
}
export declare const TooltipProvider: ({ children, forceDisable }: TooltipProviderProps) => import("react/jsx-runtime").JSX.Element;
export {};
