export function extractLayerValue(morphSegments, layerField) {
  if (!layerField) return null;
  if (!morphSegments || morphSegments.length === 0) return null;

  const values = morphSegments
    .map((seg) => seg?.[layerField])
    .filter((v) => v != null && v !== '');

  if (values.length === 0) return null;
  return values.join(' + ');
}

export function showLayerValue(token, value, layer) {
  const wrapper = document.createElement('span');
  wrapper.className = 'layer-value';
  wrapper.textContent = value;
  wrapper.dir = 'ltr';

  if (layer?.colorMap) {
    const colorKey = value.split(' + ')[0];
    const colorClass = `${layer.field}-${colorKey}`;
    wrapper.classList.add(colorClass);
    if (!layer.colorMap[colorKey] && layer.colorMap.default) {
      wrapper.classList.add(`${layer.field}-default`);
    }
  } else if (layer?.field) {
    wrapper.classList.add(`${layer.field}-value`);
  }

  token.textContent = '';
  token.appendChild(wrapper);
  token.className = 'token';
}

export function showAnnotation(token, annotationText, annotationId) {
  const wrapper = document.createElement('span');
  wrapper.className = 'annotation-text';
  wrapper.dir = 'ltr';
  wrapper.textContent = annotationText;

  token.textContent = '';
  token.appendChild(wrapper);
  token.classList.add('annotated');

  if (annotationId) {
    token.dataset.annotationId = annotationId;
  }
}

