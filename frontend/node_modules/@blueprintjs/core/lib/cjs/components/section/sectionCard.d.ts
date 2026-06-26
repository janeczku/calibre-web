import { type HTMLDivProps, type Props } from "../../common/props";
export interface SectionCardProps extends Props, HTMLDivProps, React.RefAttributes<HTMLDivElement> {
    /**
     * Whether to apply visual padding inside the content container element.
     *
     * @default true
     */
    padded?: boolean;
}
/**
 * Section card component.
 *
 * @see https://blueprintjs.com/docs/#core/components/section.section-card
 */
export declare const SectionCard: React.FC<SectionCardProps>;
