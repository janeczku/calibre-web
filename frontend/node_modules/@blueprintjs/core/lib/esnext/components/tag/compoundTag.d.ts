import type { TagSharedProps } from "./tagSharedProps";
export interface CompoundTagProps extends TagSharedProps, React.RefAttributes<HTMLSpanElement>, React.HTMLAttributes<HTMLSpanElement> {
    /**
     * Child nodes which will be rendered on the right side of the tag (e.g. the "value" in a key-value pair).
     */
    children: React.ReactNode;
    /**
     * Content to be rendered on the left side of the tag (e.g. the "key" in a key-value pair).
     * This prop must be defined; if you have no content to show here, then use a `<Tag>` instead.
     */
    leftContent: React.ReactNode;
    /**
     * Click handler for remove button.
     * The remove button will only be rendered if this prop is defined.
     */
    onRemove?: (e: React.MouseEvent<HTMLButtonElement>, tagProps: CompoundTagProps) => void;
}
/**
 * Compound tag component.
 *
 * @see https://blueprintjs.com/docs/#core/components/compound-tag
 */
export declare const CompoundTag: React.FC<CompoundTagProps>;
