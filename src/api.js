export async function api(path, method = 'GET', body) {
  const response = await fetch('/api' + path, {
    method, credentials: 'same-origin',
    headers: { 'Content-Type': 'application/json', 'X-Parking-Client': 'admin' },
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  const data = await response.json();
  if (!response.ok) {
    if (response.status === 401) window.dispatchEvent(new Event('parking:unauthorized'));
    throw new Error(typeof data.detail === 'string' ? data.detail : 'Check the entered values and dates.');
  }
  return data;
}

export async function readPlatePhoto(photo) {
  const form = new FormData();
  form.append('photo', photo);
  const response = await fetch('/api/recognition/photo', {
    method: 'POST', credentials: 'same-origin',
    headers: { 'X-Parking-Client': 'admin' }, body: form,
  });
  const data = await response.json();
  if (!response.ok) {
    if (response.status === 401) window.dispatchEvent(new Event('parking:unauthorized'));
    throw new Error(typeof data.detail === 'string' ? data.detail : 'Could not read the photo.');
  }
  return data;
}
