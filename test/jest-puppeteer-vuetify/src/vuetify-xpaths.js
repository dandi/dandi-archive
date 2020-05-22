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
 * @param {any} content the content of the element to form a predicate for
 */
function contentsAsPredicate(content) {
  if (Array.isArray(content)) {
    return content.map((c) => contentsAsPredicate(c)).join('');
  }
  if (typeof content === 'string') {
    if (isXPath(content)) {
      return `[.${content}]`;
    }
    return `[contains(text(),"${content}")]`;
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

/**
 * Formats an element of a component as a XPath predicate.
 * Vuetify components will generally have this structure for sub-elements,
 * so this helper saves a lot of boilerplate.
 *
 * @param {String} name the name of the Vuetify component
 * @param {String} element the name of the element
 * @param {String} value the contents of the element
 */
function elementAsPredicate(name, element, value) {
  return (value) ? `[.//*[@class='${name}__${element}']${contentsAsPredicate(value)}]` : '';
}

/**
 * Formats a list of elements of a component as a XPath predicate.
 * This is a wrapper for elementAsPredicate that handles multiple elements.
 *
 * @param {*} name the name of the Vuetify component
 * @param {*} values the contents of each element
 */
function elementsAsPredicate(name, values) {
  return Object.keys(values).map((key) => elementAsPredicate(name, key, values[key])).join('');
}

/**
 * Parses the arguments to a XPath generator function.
 * If the arguments are an object, they are returned as is.
 * Otherwise, it is assumed that the argument is `content` and it is returned as
 * `{ content: args }`.
 * The second argument can optionally be specified by the calling function to change the name of
 * the default parameter.
 * For example, `v-icon`s don't have content, so `vIcon` would call `parseArguments(args, 'icon')`.
 * The result of parsed arguments of `vIcon('text')` would be `{ icon: args }` rather than
 * `{ content: args }`.
 * @param {*} args the arguments to parse
 * @param {*} defaultParam The name of the parameter to use if the argument is not an object.
 */
function parseArguments(args, defaultParam = 'content') {
  if (typeof (args) === 'object') {
    return args;
  }
  const ret = {};
  ret[defaultParam] = args;
  return ret;
}


export function vAvatar(args) {
  const { content, cssClass } = parseArguments(args);
  return `//div${classAsPredicate('v-avatar', cssClass)}[span${contentsAsPredicate(content)}]`;
}

export function vBtn(args) {
  const { content, cssClass } = parseArguments(args);
  return `//*${classAsPredicate('v-btn', cssClass)}[span${contentsAsPredicate(content)}]`;
}

export function vCard(args) {
  const {
    content,
    cssClass,
    title,
    actions,
  } = parseArguments(args);
  return `//div${classAsPredicate('v-card', cssClass)}${elementsAsPredicate('v-card', { title, actions })}${contentsAsPredicate(content)}`;
}

export function vChip(args) {
  const { content, cssClass } = parseArguments(args);
  return `//*${classAsPredicate('v-chip', cssClass)}[*[@class='v-chip__content']${contentsAsPredicate(content)}]`;
}

export function vIcon(args) {
  const { icon, cssClass } = parseArguments(args, 'icon');
  return `//*${classAsPredicate('v-icon', icon, cssClass)}`;
}

export function vListItem(args) {
  const {
    content,
    action,
    title,
    subtitle,
  } = parseArguments(args);
  return `//*${classAsPredicate('v-list-item')}${elementsAsPredicate('v-list-item', {
    content, action, title, subtitle,
  })}`;
}

export function vListItemTitle(args) {
  const { content, cssClass } = parseArguments(args);
  return `//div${classAsPredicate('v-list-item__title', cssClass)}${contentsAsPredicate(content)}`;
}

export function vTextarea(args) {
  const { label, cssClass } = parseArguments(args);
  return `//div${classAsPredicate('v-textarea', cssClass)}//div[label[contains(text(),"${label}")]]//textarea`;
}

export function vTextField(args) {
  const { label, cssClass } = parseArguments(args, 'label');
  const labelPredicate = (label) ? `[.//div[label[contains(text(),"${label}")]]]` : '';
  return `//div${classAsPredicate('v-text-field', cssClass)}${labelPredicate}//input`;
}

export function vToolbar(args) {
  const { content, cssClass } = parseArguments(args);
  return `//*${classAsPredicate('v-toolbar', cssClass)}[*[@class='v-toolbar__content']${contentsAsPredicate(content)}]`;
}
