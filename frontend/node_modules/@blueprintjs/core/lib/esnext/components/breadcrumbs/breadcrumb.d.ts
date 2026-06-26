import { type ActionProps, type LinkProps } from "../../common";
export interface BreadcrumbProps extends ActionProps<HTMLAnchorElement>, LinkProps {
    children?: React.ReactNode;
    /** Whether this breadcrumb is the current breadcrumb. */
    current?: boolean;
    /**
     * Pass through value to icon's title attribute. Should be used for breadcrumbs without
     * text or children defined.
     */
    iconTitle?: string;
}
/**
 * Breadcrumb component.
 *
 * @see https://blueprintjs.com/docs/#core/components/breadcrumbs
 */
export declare const Breadcrumb: React.FC<BreadcrumbProps>;
