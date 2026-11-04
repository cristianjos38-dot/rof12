(() => {
  // Orchestration only: it clicks the visible n8n control and does not alter
  // ROF12 policy, credentials, documents, or workflow payloads.
  const button = [...document.querySelectorAll('button, [role="button"]')]
    .find((node) => /execute workflow/i.test(node.textContent || ''));
  if (!button) throw new Error('Execute workflow control not found');
  button.click();
  return 'n8n Execute workflow clicked';
})();
