document.addEventListener('DOMContentLoaded', () => {
  const form = document.querySelector('.cm-editor');
  if (form) {
    const advanced = document.querySelector('#cm-advanced-fields');
    if (advanced) form.querySelectorAll('.cm-advanced-field').forEach(field => advanced.appendChild(field));
    const schedule = form.querySelector('[name="save_action"][value="schedule"]');
    if (schedule) schedule.addEventListener('click', () => {
      const details = document.querySelector('.cm-advanced');
      if (details) details.open = true;
    });
    form.querySelectorAll('input[type="file"]').forEach(input => {
      input.addEventListener('change', () => {
        const target = form.querySelector('[data-preview-for="' + input.id + '"]');
        if (!target) return;
        const file = input.files && input.files[0];
        if (!file) { target.hidden = true; return; }
        if (target.tagName === 'IMG') {
          if (!file.type.startsWith('image/')) { target.hidden = true; return; }
          if (target.dataset.objectUrl) URL.revokeObjectURL(target.dataset.objectUrl);
          const url = URL.createObjectURL(file);
          target.dataset.objectUrl = url;
          target.src = url;
          target.hidden = false;
        } else target.textContent = 'Selected: ' + file.name;
      });
    });
    const publish = form.querySelector('[data-confirm-publish]');
    if (publish) publish.addEventListener('click', event => {
      if (!window.confirm('Publish this content to the employee portal now?')) event.preventDefault();
    });
    form.addEventListener('submit', event => {
      if (event.defaultPrevented) return;
      const button = event.submitter;
      // A disabled submit button is NOT included in POST. Previously this
      // caused Publish now to silently fall back to draft.
      if (button && button.name === 'save_action') {
        let hidden = form.querySelector('input[type="hidden"][name="save_action"]');
        if (!hidden) {
          hidden = document.createElement('input');
          hidden.type = 'hidden'; hidden.name = 'save_action'; form.appendChild(hidden);
        }
        hidden.value = button.value;
      }
      if (button) {
        button.textContent = 'Saving…';
        // Delay disabling until the browser has collected form values.
        setTimeout(() => { button.disabled = true; }, 0);
      }
    });
  }
  document.querySelectorAll('[data-confirm-toggle]').forEach(button => {
    button.addEventListener('click', event => {
      const action = button.dataset.confirmToggle;
      if (!window.confirm(action === 'publish' ? 'Publish this item now?' : 'Unpublish this item? Employees will no longer see it.')) event.preventDefault();
    });
  });
});

document.querySelectorAll('[data-toggle-password]').forEach(btn => btn.addEventListener('click', () => { const input = document.getElementById('id_password'); if (!input) return; input.type = input.type === 'password' ? 'text' : 'password'; btn.textContent = input.type === 'password' ? 'Show' : 'Hide'; }));
