const MODAL_CLOSE_SELECTOR = "[data-demo-modal-close]";

requestAnimationFrame(() => {
  const closeButton = document.querySelector(MODAL_CLOSE_SELECTOR);
  if (closeButton instanceof HTMLButtonElement) {
    closeButton.focus();
  }
});
