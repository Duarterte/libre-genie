(() => {
  const RENDER_SCALE = 0.25; // low-res render to save GPU
  const TARGET_FPS = 24;
  const BASE_COUNT = 300;
  // Multiply computed circle sizes by this constant (values <1 make circles smaller)
  const CIRCLE_BASE_SCALE = 0.333; // about 0.33

  // create or reuse canvas
  let canvas = document.querySelector('canvas.fixed-background-allapp');
  if (!canvas) {
    canvas = document.createElement('canvas');
    canvas.className = 'fixed-background-allapp';
    canvas.style.position = 'fixed';
    canvas.style.top = '0';
    canvas.style.left = '0';
    canvas.style.zIndex = '-1';
    canvas.style.pointerEvents = 'none';
    document.body.appendChild(canvas);
  }

  const ctx = canvas.getContext('2d', { alpha: true });
  let circles = [];
  // drag state for pointer-based dragging/flick
  let isPointerDown = false;
  let pointerLastX = 0, pointerLastY = 0;
  let dragAccumX = 0, dragAccumY = 0;
  let dragAccumTime = 0;
  let dragLastTime = 0;
  const FLICK_VELOCITY_SCALE = 0.02; // tunes how much flick adds to circle velocity
  // unified pointer/touch handlers (works for mouse/touch/pen)
  function handlePointerDown(x, y) {
    isPointerDown = true;
    pointerLastX = x; pointerLastY = y;
    dragAccumX = 0; dragAccumY = 0; dragAccumTime = 0;
    dragLastTime = performance.now();
  }

  function handlePointerMove(x, y) {
    if (!isPointerDown) return;
    const now = performance.now();
    const dt = Math.max(0.001, (now - dragLastTime) / 1000);
    const dx = x - pointerLastX;
    const dy = y - pointerLastY;
    pointerLastX = x; pointerLastY = y;
    dragLastTime = now;
    dragAccumX += dx; dragAccumY += dy; dragAccumTime += dt;
    // move circles by the pointer delta so they follow the drag exactly
    for (let i = 0; i < circles.length; i++) {
      circles[i].cssX += dx;
      circles[i].cssY += dy;
    }
  }

  function handlePointerUp() {
    // No flick impulse: dragging only changes position.
    // Reset drag accumulators.
    dragAccumX = 0; dragAccumY = 0; dragAccumTime = 0; dragLastTime = 0;
    isPointerDown = false;
  }

  // pointer events
  window.addEventListener('pointerdown', (e) => handlePointerDown(e.clientX, e.clientY));
  window.addEventListener('pointermove', (e) => handlePointerMove(e.clientX, e.clientY));
  window.addEventListener('pointerup', handlePointerUp);
  window.addEventListener('pointercancel', handlePointerUp);

  // touch fallback (some mobile browsers may not fire pointer events reliably)
  window.addEventListener('touchstart', (e) => {
    if (!e.touches || !e.touches[0]) return;
    handlePointerDown(e.touches[0].clientX, e.touches[0].clientY);
  }, { passive: true });
  window.addEventListener('touchmove', (e) => {
    if (!e.touches || !e.touches[0]) return;
    // prevent page scrolling while dragging
    if (isPointerDown) e.preventDefault();
    handlePointerMove(e.touches[0].clientX, e.touches[0].clientY);
  }, { passive: false });
  window.addEventListener('touchend', (e) => { handlePointerUp(); }, { passive: true });
  window.addEventListener('touchcancel', (e) => { handlePointerUp(); }, { passive: true });
  let lastRenderTime = 0;
  const frameInterval = 1000 / TARGET_FPS;

  const pickHue = () => {
    // palette: cool purples, teals, warm amber — avoid bright pinks
    const base = [220, 260, 190, 40]; // indigo, violet, teal, amber
    return base[Math.floor(Math.random() * base.length)] + (Math.random() * 30 - 15);
  };

  function resize() {
    const cssW = Math.max(1, window.innerWidth);
    const cssH = Math.max(1, window.innerHeight);
    const dpr = window.devicePixelRatio || 1;
    const scale = Math.max(0.05, Math.min(1, RENDER_SCALE));
    const bufferW = Math.max(1, Math.floor(cssW * dpr * scale));
    const bufferH = Math.max(1, Math.floor(cssH * dpr * scale));

    // keep CSS size full-screen but render to smaller buffer
    canvas.style.width = cssW + 'px';
    canvas.style.height = cssH + 'px';
    canvas.width = bufferW;
    canvas.height = bufferH;

    // transform so we draw in CSS pixels (makes positions crisp relative to chosen buffer)
    const transformScale = bufferW / cssW; // equals dpr * scale
    ctx.setTransform(transformScale, 0, 0, transformScale, 0, 0);
    ctx.imageSmoothingEnabled = true;

    // adapt circle count to viewport area
    const areaRatio = (cssW * cssH) / (1920 * 1080);
    const count = Math.max(6, Math.round(BASE_COUNT * Math.min(2, areaRatio)));
    while (circles.length < count) circles.push(new Circle());
    while (circles.length > count) circles.pop();
    // nudge re-init occasionally to adapt to new sizes
    circles.forEach(c => c.onResize && c.onResize());
  }

  class Circle {
    constructor() { this.init(true); }

    init(first = false) {
      const cssW = window.innerWidth;
      const cssH = window.innerHeight;

      // random size (CSS pixels)
      const minSize = Math.max(50, Math.min(120, (cssW + cssH) * 0.02));
      const maxSize = Math.max(120, Math.min(320, (cssW + cssH) * 0.05));
      this.size = (Math.random() * (maxSize - minSize) + minSize) * CIRCLE_BASE_SCALE;

      // spawn: 70% spawn off-screen near top/right, 30% spawn random inside for pops
      if (Math.random() < 0.7) {
        this.x = cssW + Math.random() * cssW * 0.4; // right of screen
        this.y = -Math.random() * cssH * 0.6; // above screen
      } else {
        this.x = Math.random() * cssW;
        this.y = Math.random() * cssH;
      }

      // color + tone
      this.hue = pickHue();
      this.saturation = 30 + Math.random() * 40;
      this.light = 30 + Math.random() * 25;

      // motion: mostly top-right -> bottom-left but with variability
      const baseSpeed = 0.2 + Math.random() * 0.9;
      this.vx = -(0.6 + Math.random() * 1.4) * baseSpeed;
      this.vy = (0.2 + Math.random() * 0.9) * baseSpeed;
      this.drift = (Math.random() - 0.5) * 0.7;

      // lifecycle for pop/fade
      this.birth = performance.now();
      this.life = 6 + Math.random() * 14; // seconds
      this.fadeIn = Math.max(0.2, this.life * 0.08);
      this.opacity = 0.06 + Math.random() * 0.35;

      // small initial pop scale
      this.popScale = 0.9 + Math.random() * 0.5;

      // store css coords used for drawing
      this.cssX = this.x;
      this.cssY = this.y;
      this._first = first;
    }

    onResize() {
      // reposition proportionally (simple re-init is fine)
      this.init();
    }

    update(deltaSec) {
      // time-based motion (CSS coords)
      const now = performance.now();
      const t = (now - this.birth) / 1000;
      // gentle sine drift for smoky illusion
      const sway = Math.sin((this.cssY + now * 0.002) * 0.01) * 6;
      this.cssX += (this.vx * 60 * deltaSec) + this.drift * 8 * deltaSec + sway * 0.02;
      this.cssY += (this.vy * 60 * deltaSec);

      // previously used attraction here; drag movement now applied directly from pointermove

      // slight pulsing at birth
      const p = Math.min(1, t / Math.max(0.01, this.fadeIn));
      this.currentSize = this.size * (this.popScale * (1 - 0.6 * p) + 0.6);

      // if out of bounds or finished life, reset
      const cssW = window.innerWidth, cssH = window.innerHeight;
      if (this.cssX < -this.currentSize * 1.2 || this.cssY > cssH + this.currentSize * 1.2 || t > this.life) {
        this.init();
      }
    }

    draw() {
      const now = performance.now();
      const age = (now - this.birth) / 1000;
      const progress = Math.max(0, Math.min(1, age / this.life));
      // smooth in/out alpha
      let alpha = this.opacity;
      if (age < this.fadeIn) alpha *= age / this.fadeIn;
      if (progress > 0.85) alpha *= Math.max(0, (1 - (progress - 0.85) / 0.15));

      const x = this.cssX;
      const y = this.cssY;
      const r = Math.max(1, this.currentSize || this.size);

      // radial gradient for soft glow
      const g = ctx.createRadialGradient(x, y, 0, x, y, r);
      const stop0 = `hsla(${this.hue}, ${this.saturation}%, ${Math.min(70, this.light+10)}%, ${alpha})`;
      const stop1 = `hsla(${this.hue + 30}, ${Math.max(20,this.saturation-10)}%, ${Math.min(55,this.light+5)}%, ${Math.max(0, alpha * 0.0)})`;
      g.addColorStop(0, stop0);
      g.addColorStop(0.6, stop0);
      g.addColorStop(1, stop1);

      ctx.beginPath();
      ctx.fillStyle = g;
      ctx.arc(x, y, r, 0, Math.PI * 2);
      ctx.fill();
    }
  }

  // setup & animate
  function setup() {
    resize();
    // create exactly the number resize decided
    if (!circles.length) {
      const cssW = Math.max(1, window.innerWidth);
      const cssH = Math.max(1, window.innerHeight);
      const areaRatio = (cssW * cssH) / (1920 * 1080);
      const count = Math.max(6, Math.round(BASE_COUNT * Math.min(2, areaRatio)));
      circles = Array.from({ length: count }, () => new Circle());
    }
  }

  function animate(now) {
    if (!lastRenderTime) lastRenderTime = now;
    const deltaMs = now - lastRenderTime;
    if (deltaMs < frameInterval) {
      requestAnimationFrame(animate);
      return;
    }
    const deltaSec = deltaMs / 1000;
    lastRenderTime = now;

    // clear pixel buffer correctly regardless of current transform
    ctx.save();
    ctx.setTransform(1, 0, 0, 1, 0, 0);           // reset transform to identity
    ctx.clearRect(0, 0, canvas.width, canvas.height); // clear full backing buffer
    ctx.restore();                                // restore previous transform

    for (let i = 0; i < circles.length; i++) {
      circles[i].update(deltaSec);
      circles[i].draw();
    }

    requestAnimationFrame(animate);
  }

  // pause when hidden
  document.addEventListener('visibilitychange', () => {
    if (document.hidden) lastRenderTime = 0;
  });

  let resizeTimer = null;
  window.addEventListener('resize', () => {
    clearTimeout(resizeTimer);
    resizeTimer = setTimeout(resize, 120);
  });

  setup();
  requestAnimationFrame(animate);
})();