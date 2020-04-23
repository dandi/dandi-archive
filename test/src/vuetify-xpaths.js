const _xpath_regex = /\/\/[a-z*]+(\[.*\])*/;

function isXPath(text) {
  return _xpath_regex.test(text);
}

/**
 * Formats an argument into one or more XPath predicates.
 * If the argument is a valid XPath, then the predicate will match all elements that contain the element identified by that XPath.
 * If the argument is any other string, then the predicate will match all elements that contain that string in their text bodies.
 * If the argument is an array, the function is called recursively and multiple predicates are returned in the same string.
 *
 * @param {any} contents the contents of the element to form a predicate for
 */
function contentsAsPredicate(contents) {
  if (Array.isArray(contents)) {
    return contents.map(c => contentsAsPredicate(c)).join('');
  }
  if (typeof contents === 'string') {
    if (isXPath(contents)) {
      return `[.${contents}]`;
    } else {
      return `[contains(text(),"${contents}")]`;
    }
  }
  return '';
}

/**
 * Formats a list of CSS classes into XPath predicates.
 *
 * @param  {...any} classes the CSS classes to form a predicate for
 */
function classAsPredicate(...classes) {
  return classes.map(cssClass => {
    if (Array.isArray(cssClass)) {
      return cssClass.map(c => classAsPredicate(c)).join('');
    }
    if (typeof cssClass === 'string') {
      return `[contains(@class, "${cssClass}")]`;
    }
    return '';
  }).join('');
}

export function vAvatar(contents, cssClass = undefined) {
  return `//div${classAsPredicate('v-avatar', cssClass)}[span${contentsAsPredicate(contents)}]`;
}

export function vBtn(contents, cssClass = undefined) {
  return `//*${classAsPredicate('v-btn', cssClass)}[span${contentsAsPredicate(contents)}]`;
}

export function vIcon(icon, cssClass = undefined) {
  return `//i${classAsPredicate('v-icon', icon, cssClass)}`;
}

export function vListItem(contents, action = undefined) {
  return `//div${classAsPredicate('v-list-item')}[div[@class='v-list-item__content']${contentsAsPredicate(contents)}][div[@class='v-list-item__action']${contentsAsPredicate(action)}]`;
}

export function vTextField(label, cssClass = undefined) {
  return `//div${classAsPredicate('v-text-field', cssClass)}//div[label[contains(text(),"${label}")]]/input`;
}
