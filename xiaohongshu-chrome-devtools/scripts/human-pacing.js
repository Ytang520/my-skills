async (options = {}) => {
  const config = {
    minDelayMs: 700,
    maxDelayMs: 1800,
    jitterRatio: 0.25,
    minScrollPx: 220,
    maxScrollPx: 480,
    maxSteps: 6,
    stableRounds: 2,
    horizontalDriftPx: 15,
    ...options,
  };

  const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));
  const clamp = (value, min, max) => Math.min(max, Math.max(min, value));
  const randomBetween = (min, max) => min + Math.random() * (max - min);
  const jitter = (base) => {
    const ratio = clamp(config.jitterRatio, 0, 1);
    return base * (1 + (Math.random() * 2 - 1) * ratio);
  };
  const delay = () => jitter(randomBetween(config.minDelayMs, config.maxDelayMs));

  const history = [];
  let stableCount = 0;
  let lastY = window.scrollY;
  let lastHeight = document.body.scrollHeight;

  await sleep(delay());

  for (let step = 0; step < config.maxSteps; step += 1) {
    const scrollY = Math.floor(randomBetween(config.minScrollPx, config.maxScrollPx));
    const driftX = Math.floor(randomBetween(-config.horizontalDriftPx, config.horizontalDriftPx + 1));

    window.scrollBy(driftX, scrollY);
    await sleep(delay());

    const currentY = window.scrollY;
    const currentHeight = document.body.scrollHeight;
    const moved = currentY !== lastY;
    const heightChanged = currentHeight !== lastHeight;

    history.push({
      step: step + 1,
      scrollY: currentY,
      height: currentHeight,
      moved,
      heightChanged,
    });

    if (!moved && !heightChanged) {
      stableCount += 1;
    } else {
      stableCount = 0;
    }

    lastY = currentY;
    lastHeight = currentHeight;

    if (stableCount >= config.stableRounds) {
      break;
    }
  }

  return {
    scrollY: window.scrollY,
    height: document.body.scrollHeight,
    stable: stableCount >= config.stableRounds,
    steps: history.length,
    history,
  };
}
