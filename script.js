// Fetch from the FastAPI backend and render results into the page
async function fetchAndRender(endpoint, containerId) {
  const container = document.getElementById(containerId);
  if (!container) return;
  container.textContent = 'Loading...';
  try {
    const res = await fetch(`http://127.0.0.1:8000/${endpoint}`);
    if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
    const data = await res.json();
    renderTable(container, data);
  } catch (err) {
    console.error('Error fetching', endpoint, err);
    container.textContent = 'Error loading data';
  }
}

function renderTable(container, data) {
  if (!Array.isArray(data) || data.length === 0) {
    container.textContent = data && Object.keys(data).length ? JSON.stringify(data) : 'No data';
    return;
  }
  // build table from keys of first object
  const cols = Object.keys(data[0]);
  const table = document.createElement('table');
  table.className = 'data-table';
  const thead = document.createElement('thead');
  const hrow = document.createElement('tr');
  cols.forEach(c => { const th = document.createElement('th'); th.textContent = c; hrow.appendChild(th); });
  thead.appendChild(hrow);
  table.appendChild(thead);

  const tbody = document.createElement('tbody');
  data.forEach(row => {
    const tr = document.createElement('tr');
    cols.forEach(c => {
      const td = document.createElement('td');
      let v = row[c];
      if (typeof v === 'object' && v !== null) v = JSON.stringify(v);
      td.textContent = v === undefined ? '' : v;
      tr.appendChild(td);
    });
    tbody.appendChild(tr);
  });
  table.appendChild(tbody);

  // clear and append
  container.innerHTML = '';
  container.appendChild(table);
}

// Kick off fetches
window.addEventListener('DOMContentLoaded', () => {
  fetchAndRender('bat', 'bat-container');
  fetchAndRender('autos', 'autos-container');
  fetchAndRender('tags', 'tags-container');
  fetchAndRender('loc', 'loc-container');
});