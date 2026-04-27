export function initHeroAnimation() {
  const canvas = document.getElementById("ascii-bg");
  if (!canvas) return;
  const ctx = canvas.getContext("2d");

  let width, height, columns, rows;
  const fontSize = 18;
  const chars = ".,-~:;=!*#$@".split("");

  let grid = [];

  function resize() {
    width = canvas.width = window.innerWidth;
    height = canvas.height = window.innerHeight;

    // Spaced out: columns and rows calculated with larger multipliers
    columns = Math.floor(width / (fontSize * 1.5));
    rows = Math.floor(height / (fontSize * 1.8));

    grid = [];
    for (let r = 0; r < rows; r++) {
      grid[r] = [];
      for (let c = 0; c < columns; c++) {
        grid[r][c] = {
          char: chars[Math.floor(Math.random() * chars.length)],
          opacity: 0.1 + Math.random() * 0.2,
        };
      }
    }
  }

  window.addEventListener("resize", resize);
  resize();
  setTimeout(resize, 500);

  // Fade in when fully loaded
  function showCanvas() {
    canvas.classList.remove("opacity-0");
    canvas.classList.add("opacity-100");
  }

  if (document.readyState === "complete") {
    showCanvas();
  } else {
    window.addEventListener("load", showCanvas);
  }

  function draw() {
    if (grid.length === 0) return;

    // White background
    ctx.fillStyle = "white";
    ctx.fillRect(0, 0, width, height);

    // Regular weight font
    ctx.font = fontSize + "px 'IBM Plex Mono', monospace";

    for (let r = 0; r < rows; r++) {
      for (let c = 0; c < columns; c++) {
        const cell = grid[r][c];
        if (!cell) continue;

        // Slower character changes
        if (Math.random() > 0.99) {
          cell.char = chars[Math.floor(Math.random() * chars.length)];
        }

        // Slower, smoother opacity shimmer
        cell.opacity += (Math.random() - 0.5) * 0.05;
        cell.opacity = Math.max(0.05, Math.min(0.3, cell.opacity));

        // Gray characters
        const grayValue = 160 + Math.floor(Math.random() * 40);
        ctx.fillStyle = `rgba(${grayValue}, ${grayValue}, ${grayValue}, ${cell.opacity})`;
        ctx.fillText(cell.char, c * fontSize * 1.5, (r + 1) * fontSize * 1.8);
      }
    }
  }

  let lastTime = 0;
  const fps = 10;
  const interval = 1000 / fps;

  function animate(time) {
    if (time - lastTime >= interval) {
      draw();
      lastTime = time;
    }
    requestAnimationFrame(animate);
  }

  animate(0);
}
