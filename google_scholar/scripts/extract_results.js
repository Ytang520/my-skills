async () => {
  const options = globalThis.__GS_EXTRACT_OPTIONS__ || {};
  const offset = Number.isFinite(Number(options.start)) ? Number(options.start) : 0;
  const page = Number.isFinite(Number(options.page)) ? Number(options.page) : Math.floor(offset / 10) + 1;

  for (let i = 0; i < 20; i += 1) {
    if (document.querySelector('#gs_res_ccl') || document.querySelector('#gs_captcha_ccl')) break;
    await new Promise((resolve) => setTimeout(resolve, 500));
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

  const items = Array.from(document.querySelectorAll('#gs_res_ccl .gs_r.gs_or.gs_scl'));
  const results = items.map((item, index) => {
    const titleLink = item.querySelector('.gs_rt a');
    const titleContainer = item.querySelector('.gs_rt');
    const meta = item.querySelector('.gs_a')?.textContent?.trim() || '';
    const parts = meta.split(' - ');
    const citedByLink = item.querySelector('.gs_fl a[href*="cites"]');
    const relatedLink = item.querySelector('.gs_fl a[href*="related"]');
    const versionsLink = item.querySelector('.gs_fl a[href*="cluster"]');
    const fullTextLink = item.querySelector('.gs_ggs a') || item.querySelector('.gs_or_ggsm a');

    return {
      n: offset + index + 1,
      title: titleLink?.textContent?.trim() || titleContainer?.textContent?.trim() || '',
      href: titleLink?.href || '',
      authors: parts[0]?.trim() || '',
      journalYear: parts[1]?.trim() || '',
      citedBy: citedByLink?.textContent?.match(/\d+/)?.[0] || '0',
      citedByUrl: citedByLink?.href || '',
      dataCid: item.getAttribute('data-cid') || '',
      fullTextUrl: fullTextLink?.href || '',
      fullTextType: fullTextLink?.querySelector('span.gs_ctg2')?.textContent?.trim() || '',
      snippet: item.querySelector('.gs_rs')?.textContent?.trim()?.substring(0, 300) || '',
      relatedUrl: relatedLink?.href || '',
      versionsUrl: versionsLink?.href || '',
      versions: versionsLink?.textContent?.match(/\d+/)?.[0] || ''
    };
  });

  const total = document.querySelector('#gs_ab_md')?.textContent?.trim() || '';
  const hasNext = Boolean(
    document.querySelector('#gs_n a.gs_ico_nav_next') ||
    Array.from(document.querySelectorAll('#gs_n a')).some((link) => /Next/i.test(link.textContent || link.ariaLabel || ''))
  );

  return {
    total,
    page,
    start: offset,
    resultCount: results.length,
    hasNext,
    currentUrl: window.location.href,
    results
  };
}
