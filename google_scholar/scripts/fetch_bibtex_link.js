async () => {
  const options = globalThis.__GS_EXTRACT_OPTIONS__ || {};
  const cid = String(options.cid || '').trim();

  if (!cid) {
    return {
      error: 'missing_cid',
      message: 'A Google Scholar data-cid is required to fetch the cite dialog.'
    };
  }

  const bodyText = document.body?.innerText || '';
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

  const response = await fetch(
    `https://scholar.google.com/scholar?q=info:${encodeURIComponent(cid)}:scholar.google.com/&output=cite`,
    { credentials: 'include' }
  );
  const html = await response.text();

  if (/recaptcha|unusual traffic|gs_captcha_ccl|not a robot/i.test(html)) {
    return {
      error: 'captcha',
      message: 'Google Scholar requires human verification while opening the cite dialog.',
      currentUrl: window.location.href
    };
  }

  const doc = new DOMParser().parseFromString(html, 'text/html');
  const links = Array.from(doc.querySelectorAll('#gs_citi a')).map((link) => ({
    format: link.textContent?.trim() || '',
    url: link.href || ''
  }));
  const citations = Array.from(doc.querySelectorAll('#gs_citt tr')).map((row) => {
    const cells = row.querySelectorAll('td');
    return {
      style: cells[0]?.textContent?.trim() || '',
      text: cells[1]?.textContent?.trim() || ''
    };
  });
  const bibtexLink = links.find((link) => link.format === 'BibTeX') || null;

  return {
    cid,
    bibtexLink: bibtexLink?.url || '',
    links,
    citations
  };
}
