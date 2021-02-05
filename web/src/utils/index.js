function getLocationFromRoute(route) {
  const { _modelType, _id } = route.query;
  if (_modelType && _id) {
    return { _modelType, _id };
  }
  return null;
}

function getPathFromLocation(location) {
  if (!location) {
    return '/';
  }
  return `/${location._modelType || location.type}${location._id ? `/${location._id}` : ''}`;
}

function getSelectedFromRoute(route) {
  const { ids } = route.params;
  return ids ? ids.split('/').map((item) => item.split('+')).map(([type, id]) => ({ _id: id, _modelType: type })) : [];
}

function getPathFromSelected(selected) {
  if (!selected.length) {
    return '';
  }
  return `/selected/${selected.map((model) => `${model._modelType}+${model._id}`).join('/')}`;
}

// https://stackoverflow.com/a/33928558/1643850 with slight modification
function copyToClipboard(text) {
  if (window.clipboardData && window.clipboardData.setData) {
    // Internet Explorer-specific code path to prevent textarea being shown while dialog is visible.
    return window.clipboardData.setData('Text', text);
  } if (document.queryCommandSupported && document.queryCommandSupported('copy')) {
    const textarea = document.createElement('textarea');
    textarea.textContent = text;
    textarea.style.position = 'fixed'; // Prevent scrolling to bottom of page in Microsoft Edge.
    document.body.appendChild(textarea);
    textarea.select();
    try {
      return document.execCommand('copy'); // Security exception may be thrown by some browsers.
    } catch (e) {
      return false;
    } finally {
      document.body.removeChild(textarea);
    }
  }
  return false;
}

function getDandisetContact(dandiset) {
  if (dandiset.meta.dandiset.contributors) {
    const contact = dandiset.meta.dandiset.contributors.find((cont) => cont.roles && cont.roles.includes('ContactPerson'));

    if (!contact) return null;
    return contact.name;
  }

  return null;
}

const dandisetHasVersion = (versions, version) => {
  const versionNumbers = versions.map((v) => v.version);
  return versionNumbers.includes(version);
};

export {
  getLocationFromRoute,
  getPathFromLocation,
  getSelectedFromRoute,
  getPathFromSelected,
  copyToClipboard,
  getDandisetContact,
  dandisetHasVersion,
};
