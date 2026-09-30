async () => {
  const options = globalThis.__GS_EXTRACT_OPTIONS__ || {};
  const targetCid = String(options.cid || '').trim();
  const targetIndex = Number.isFinite(Number(options.index)) ? Number(options.index) : null;

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

  const items = Array.from(document.querySelectorAll('#gs_res_ccl .gs_r.gs_or.gs_scl'));
  let item = null;

  if (targetCid) {
    item = items.find((candidate) => candidate.getAttribute('data-cid') === targetCid) || null;
  }

  if (!item && targetIndex !== null) {
    item = items[targetIndex - 1] || null;
  }

  if (!item && items.length === 1) {
    item = items[0];
  }

  if (!item) {
    return {
      error: 'not_found',
      message: 'Target paper was not found on the current Google Scholar results page.',
      currentUrl: window.location.href
    };
  }

  const titleLink = item.querySelector('.gs_rt a');
  const fullTextLink = item.querySelector('.gs_ggs a') || item.querySelector('.gs_or_ggsm a');
  const paperUrl = titleLink?.href || '';
  const fullTextUrl = fullTextLink?.href || '';
  const fullTextType = fullTextLink?.querySelector('span.gs_ctg2')?.textContent?.trim() ||
    (fullTextUrl.toLowerCase().includes('.pdf') ? '[PDF]' : (fullTextUrl ? '[HTML]' : ''));
  const meta = item.querySelector('.gs_a')?.textContent || '';
  const parts = meta.split(' - ');

  let doi = '';
  if (/doi\.org\//i.test(paperUrl)) {
    doi = paperUrl.replace(/^https?:\/\/(dx\.)?doi\.org\//i, '');
  }

  const links = {};
  if (fullTextUrl) {
    links.fullText = fullTextUrl;
    links.fullTextType = fullTextType;
  }
  if (paperUrl) links.publisher = paperUrl;
  if (doi) {
    links.doi = `https://doi.org/${doi}`;
  }

  return {
    dataCid: item.getAttribute('data-cid') || '',
    title: titleLink?.textContent?.trim() || item.querySelector('.gs_rt')?.textContent?.trim() || '',
    authors: parts[0]?.trim() || '',
    journalYear: parts[1]?.trim() || '',
    doi,
    fullTextUrl,
    fullTextType,
    paperUrl,
    links,
    currentUrl: window.location.href
  };
}
