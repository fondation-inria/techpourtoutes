// Nothing is captured on its own: only what the page hands to `Sentry.captureException`.
// Breadcrumbs stay, so an event shows the requests that preceded it and their status.
const AUTOMATIC_CAPTURE = ["GlobalHandlers", "BrowserApiErrors", "BrowserSession"];

Sentry.init({
  dsn: document.currentScript.dataset.dsn,
  sendDefaultPii: false,
  integrations: (defaults) => defaults.filter((integration) => !AUTOMATIC_CAPTURE.includes(integration.name)),
});
