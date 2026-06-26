type InteractiveHTMLAttributes<E extends HTMLElement> = Pick<React.HTMLAttributes<E>, "onBlur" | "onClick" | "onFocus" | "onKeyDown" | "onKeyUp" | "tabIndex">;
interface InteractiveComponentProps extends InteractiveHTMLAttributes<HTMLElement> {
    active?: boolean | undefined;
}
interface InteractiveAttributes<E extends HTMLElement> extends InteractiveHTMLAttributes<E> {
    ref: React.Ref<E>;
}
export interface UseInteractiveAttributesOptions {
    defaultTabIndex: number | undefined;
    disabledTabIndex: number | undefined;
}
export declare function useInteractiveAttributes<E extends HTMLElement>(interactive: boolean, props: InteractiveComponentProps, ref: React.Ref<E>, options?: UseInteractiveAttributesOptions): [active: boolean, interactiveProps: InteractiveAttributes<E>];
export {};
