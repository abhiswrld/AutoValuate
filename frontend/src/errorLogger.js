window.addEventListener('error', (event) => {
  fetch('http://localhost:5176/__log_error', {
    method: 'POST',
    body: JSON.stringify({ message: event.message, filename: event.filename, lineno: event.lineno })
  });
});
