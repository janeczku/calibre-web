import * as IconSvgPaths16 from "./generated/16px/paths";
import * as IconSvgPaths20 from "./generated/20px/paths";
import type { IconName } from "./iconNames";
import { type IconPaths, IconSize } from "./iconTypes";
import type { PascalCase } from "./type-utils";
export { IconSvgPaths16, IconSvgPaths20 };
/**
 * Get the list of vector paths that define a given icon. These path strings are used to render `<path>`
 * elements inside an `<svg>` icon element. For full implementation details and nuances, see the icon component
 * handlebars template and `generate-icon-components` script in the __@blueprintjs/icons__ package.
 *
 * Note: this function loads all icon definitions __statically__, which means every icon is included in your
 * JS bundle. Only use this API if your app is likely to use all Blueprint icons at runtime. If you are looking for a
 * dynamic icon loader which loads icon definitions on-demand, use `{ Icons } from "@blueprintjs/icons"` instead.
 */
export declare function getIconPaths(name: IconName, size: IconSize): IconPaths;
/**
 * Type safe string literal conversion of snake-case icon names to PascalCase icon names.
 * This is useful for indexing into the SVG paths record to extract a single icon's SVG path definition.
 *
 * @deprecated use `getIconPaths` instead
 */
export declare function iconNameToPathsRecordKey(name: IconName): PascalCase<IconName>;
