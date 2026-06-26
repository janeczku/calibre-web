import { type HTMLDivProps, type Props } from "../../common";
export interface CardListProps extends Props, HTMLDivProps, React.RefAttributes<HTMLDivElement> {
    /**
     * Whether this container element should have a visual border.
     *
     * Set this to `false` to remove elevation and border radius styles, which allows this element to be a child of
     * another bordered container element without padding (like SectionCard). Note that this also sets a 1px margin
     * _in dark theme_ to account for inset box shadows in that theme used across the design system. Be sure to test
     * your UI in both light and dark theme if you modify this prop value.
     *
     * @default true
     */
    bordered?: boolean;
    /**
     * Whether this component should use compact styles with reduced visual padding.
     *
     * Note that this prop affects styling for all Cards within this CardList and you do not need to set the
     * `compact` prop individually on those child Cards.
     *
     * @default false
     */
    compact?: boolean;
}
export declare const CardList: React.FC<CardListProps>;
