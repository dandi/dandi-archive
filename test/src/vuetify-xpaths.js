import './jest-xpaths';

const xpathRegex = /\/\/[a-z*]+(\[.*\])*/;

function isXPath(text) {
  return xpathRegex.test(text);
}

/**
 * Formats an argument into one or more XPath predicates.
 * If the argument is a valid XPath, then the predicate will match all elements that contain the
 * element identified by that XPath.
 * If the argument is any other string, then the predicate will match all elements that contain
 * that string in their text bodies.
 * If the argument is an array, the function is called recursively and multiple predicates are
 * returned in the same string.
 *
 * @param {any} contents the contents of the element to form a predicate for
 */
function contentsAsPredicate(contents) {
  if (Array.isArray(contents)) {
    return contents.map((c) => contentsAsPredicate(c)).join('');
  }
  if (typeof contents === 'string') {
    if (isXPath(contents)) {
      return `[.${contents}]`;
    }
    return `[contains(text(),"${contents}")]`;
  }
  return '';
}

/**
 * Formats a list of CSS classes into XPath predicates.
 *
 * @param  {...any} classes the CSS classes to form a predicate for
 */
function classAsPredicate(...classes) {
  return classes.map((cssClass) => {
    if (Array.isArray(cssClass)) {
      return cssClass.map((c) => classAsPredicate(c)).join('');
    }
    if (typeof cssClass === 'string') {
      return `[contains(concat(" ",@class," "), " ${cssClass} ")]`;
    }
    return '';
  }).join('');
}

export function vAvatar(contents, { cssClass } = {}) {
  return `//div${classAsPredicate('v-avatar', cssClass)}[span${contentsAsPredicate(contents)}]`;
}

export function vBtn(contents, { cssClass } = {}) {
  return `//*${classAsPredicate('v-btn', cssClass)}[span${contentsAsPredicate(contents)}]`;
}

export function vCard(contents, { cssClass, title, actions } = {}) {
  const titlePredicate = (title) ? `[div[@class='v-card__title']${contentsAsPredicate(title)}]` : '';
  const actionsPredicate = (actions) ? `[div[@class='v-card__actions']${contentsAsPredicate(actions)}]` : '';
  return `//div${classAsPredicate('v-card', cssClass)}${titlePredicate}${actionsPredicate}${contentsAsPredicate(contents)}`;
}

export function vChip(contents, { cssClass } = {}) {
  return `//*${classAsPredicate('v-chip', cssClass)}[*[@class='v-chip__content']${contentsAsPredicate(contents)}]`;
}

export function vIcon(icon, { cssClass } = {}) {
  return `//*${classAsPredicate('v-icon', icon, cssClass)}`;
}

export function vListItem(contents, { action, title, subtitle } = {}) {
  const contentsPredicate = (contents) ? `[.//div[@class='v-list-item__content']${contentsAsPredicate(contents)}]` : '';
  const actionPredicate = (action) ? `[.//div[@class='v-list-item__action']${contentsAsPredicate(action)}]` : '';
  const titlePredicate = (title) ? `[.//div[@class='v-list-item__title']${contentsAsPredicate(title)}]` : '';
  const subtitlePredicate = (subtitle) ? `[//div[@class='v-list-item__subtitle']${contentsAsPredicate(subtitle)}]` : '';
  return `//*${classAsPredicate('v-list-item')}${contentsPredicate}${actionPredicate}${titlePredicate}${subtitlePredicate}`;
}

export function vListItemTitle(contents, { cssClass } = {}) {
  return `//div${classAsPredicate('v-list-item__title', cssClass)}${contentsAsPredicate(contents)}`;
}

export function vTextarea(label, { cssClass } = {}) {
  return `//div${classAsPredicate('v-textarea', cssClass)}//div[label[contains(text(),"${label}")]]//textarea`;
}


export function vTextField(label, { cssClass } = {}) {
  const labelPredicate = (label) ? `[.//div[label[contains(text(),"${label}")]]]` : '';
  return `//div${classAsPredicate('v-text-field', cssClass)}${labelPredicate}//input`;
}

export function vToolbar(contents, { cssClass } = {}) {
  return `//*${classAsPredicate('v-toolbar', cssClass)}[*[@class='v-toolbar__content']${contentsAsPredicate(contents)}]`;
}
