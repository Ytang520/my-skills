async () => {
  const bodyText = document.body?.innerText || document.body?.textContent || '';

  if (
    document.querySelector('#gs_captcha_ccl') ||
    /recaptcha|unusual traffic|not a robot/i.test(bodyText)
  ) {
    return {
      error: 'captcha',
      message: 'Google Scholar requires human verification.',
      currentUrl: window.location.href
    };
  }

  const bibtex = bodyText.trim();
  if (!bibtex) {
    return {
      error: 'empty_bibtex',
      message: 'The current page did not contain BibTeX text.',
      currentUrl: window.location.href
    };
  }

  return {
    bibtex,
    currentUrl: window.location.href
  };
}
