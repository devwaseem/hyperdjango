/** @type {import('tailwindcss').Config} */

export default {
  content: ["./hyper/**/*.{html,js,ts,css,py}"],
  theme: {
    extend: {
      fontFamily: {
        sans: ['"IBM Plex Mono"', "ui-sans-serif", "system-ui", "sans-serif"],
        mono: ['"IBM Plex Mono"', "ui-monospace", "SFMono-Regular", "Menlo", "Monaco", "Consolas", "monospace"],
      },
    },
  },
  plugins: [],
};
