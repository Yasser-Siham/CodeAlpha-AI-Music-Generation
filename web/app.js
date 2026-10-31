const $ = id => document.getElementById(id);
$('temperature').addEventListener('input', () => $('temp-value').textContent = $('temperature').value);
async function refresh() {
  try {
    const response = await fetch('/api/status');
    if (!response.ok) throw Error('Cannot read workspace status.');
    const state = await response.json();
    $('file-count').textContent = state.files;
    $('model-state').textContent = state.model ? 'Trained' : 'Untrained';
    $('status').textContent = state.running ? 'Creating…' : 'Ready';
    document.body.classList.toggle('busy', state.running);
    document.querySelectorAll('[data-action]').forEach(button => button.disabled = state.running || (button.dataset.action === 'generate' && !state.model));
    const log = $('log');
    if (log.textContent !== state.log) { log.textContent = state.log; log.scrollTop = log.scrollHeight; }
    $('download').hidden = !state.result;
    if (state.result) $('result-text').textContent = 'Your composition is ready. Take it into your next session.';
    $('error').textContent = '';
  } catch (error) { $('error').textContent = 'Connection lost. Check that the local server is running.'; }
}
document.querySelectorAll('[data-action]').forEach(button => button.addEventListener('click', async () => {
  const inputs = button.dataset.action === 'train' ? [$('epochs')] : button.dataset.action === 'generate' ? [$('length'), $('temperature')] : [];
  if (inputs.some(input => !input.reportValidity())) return;
  button.disabled = true;
  try {
    const response = await fetch('/api/run', {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({action:button.dataset.action, epochs:$('epochs').value,length:$('length').value,temperature:$('temperature').value})});
    if (!response.ok) throw Error(await response.text());
    await refresh();
  } catch (error) { $('error').textContent = error.message; button.disabled = false; }
}));
refresh(); setInterval(refresh, 1500);
