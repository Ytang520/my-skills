() => {
  const timeZone = Intl.DateTimeFormat().resolvedOptions().timeZone || "";
  const language = navigator.language || "";
  const languages = Array.isArray(navigator.languages) ? navigator.languages : [];
  const viewport = {
    width: window.innerWidth,
    height: window.innerHeight,
    devicePixelRatio: window.devicePixelRatio,
  };
  const warnings = [];

  if (!location.hostname.endsWith("xiaohongshu.com") && !location.hostname.endsWith("xhslink.com")) {
    warnings.push("Current page is not a Xiaohongshu domain.");
  }

  if (!language.toLowerCase().startsWith("zh")) {
    warnings.push(`Browser language is ${language || "unknown"}, expected a Chinese locale for XHS browsing.`);
  }

  if (!languages.some((item) => String(item).toLowerCase().startsWith("zh"))) {
    warnings.push("Browser languages do not include a Chinese locale.");
  }

  if (timeZone !== "Asia/Shanghai") {
    warnings.push(`Browser timezone is ${timeZone || "unknown"}, expected Asia/Shanghai for XHS browsing.`);
  }

  if (viewport.width < 1000 || viewport.height < 700) {
    warnings.push(`Viewport is ${viewport.width}x${viewport.height}, which may be too small for stable extraction.`);
  }

  return {
    ok: warnings.length === 0,
    warnings,
    context: {
      language,
      languages,
      timeZone,
      viewport,
      url: location.href,
      host: location.hostname,
    },
  };
}
