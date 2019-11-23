function getLocationFromRoute(route) {
  const { _modelType, _id } = route.params;
  if (_modelType) {
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
  return ids ? ids.split('/').map(item => item.split('+')).map(([type, id]) => ({ _id: id, _modelType: type })) : [];
}

function getPathFromSelected(selected) {
  if (!selected.length) {
    return '';
  }
  return `/selected/${selected.map(model => `${model._modelType}+${model._id}`).join('/')}`;
}

export {
  getLocationFromRoute, getPathFromLocation, getSelectedFromRoute, getPathFromSelected,
};
